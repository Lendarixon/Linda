# SETS_BUG_REPORT — model sets: "lite shows as not installed and the download multiplies on every click"

Branch `rc/2.4`. Nothing else was touched (`engine.py`, `voters.py`, `humanize_pack.py` untouched; no push).

## Owner report

> при загрузке полного набора моделей нельзя выбирать малые, отображается что малые не скачаны,
> и попытка их скачать приводит к бесконечному скачиванию, которое плодится при каждом нажатии

## Root cause

The bug is **not** in `updater.effective()` / `wanted()` / `set_info()` — those are correct. It is in the
**cached update status** and in the **unguarded buttons**.

1. **`core.update` is never recomputed after a download finishes.** `Core.check_updates()` (`linda_desktop/app.py:180`)
   is the only place that assigns `self.update = updater.update_status(...)`, and it runs on a timer
   (`UPDATE_CHECK_HOURS`) or on an explicit `/api/update/check`. `updater.Job._run` ends with
   `phase="done"` and then calls `on_done`, which was `lambda m: (engine.unload(), preload())` — the
   `update` dict was left with the pre-download values (`weights_missing: True`,
   `bytes_to_download: 8202`). So `/api/status` kept saying "weights missing" forever, the setup screen
   stayed visible and the UI kept offering a download that had already completed.
2. **`POST /api/models/download` never checked whether anything was left to fetch.** It only checked
   `job.start()`, i.e. *is a thread alive right now*. Once the previous job had exited, a new press started a
   **fully new job** on the same manifest: re-download to `staging/<version>`, re-verify, re-apply — for files
   that were already on the disk. That is the "infinite download" and the "one more per click" multiplication
   (each press also re-fetched `latest.json` + `latest.json.sig`, visible in the repository request log).
3. **`POST /api/models/sets` could start a second job.** It called `job.start(...)` whenever
   `weights_missing` was true, without `job.running()` — and `check_updates()` immediately before it can
   already auto-start the job through `_maybe_auto_models()` (`app.py:193`, guard
   `self.job.running()`). Two starts raced; the loser silently did nothing and the UI got no feedback
   (`/api/models/sets` returned only `{"status": "ok"}`, without the job state).
4. **No button guards in the page** (`web/index.html`): `lpSetupGo.onclick` and `lpSetsApply.onclick` posted
   on every click with no disabled state and no busy check; the set radio cards stayed clickable while a job ran;
   `desktopModelsDl` (the shell CTA in `web/desktop-shell.js`) had no disabled state at all. So the user's
   repeated presses all reached the backend and produced either 409-error toasts or another full job.
5. **`weights_missing` also went stale the other way round**: after `POST /api/models/sets` removed a set, the
   status was recomputed, but nothing healed the stale "missing" flag left over from a finished download.

`updater.effective()` (only selected sets), `set_info()` (all files, computes `installed` per set from the disk)
and `files_to_fetch()` (skips files whose size+sha match the installed manifest) were verified correct with a
reproduction script: only the lite files are fetched when pro is installed, and a redundant download of an
already-complete manifest fetches **nothing** at the HTTP level — the loop was created purely by the stale
status plus the unguarded start.

## Fix

| file:line | change |
|---|---|
| `linda_desktop/app.py:93` | `job.on_done` → `Core._on_download_done` |
| `linda_desktop/app.py:152` | `_on_download_done()`: recompute `self.update = updater.update_status(self.manifest)` when a job ends, then unload/preload as before |
| `linda_desktop/app.py:166` | `Core.refresh_status()`: cheap self-heal — if the cached status says `weights_missing` but `updater.is_complete(self.manifest)` is true, recompute it (no network) |
| `linda_desktop/app.py:336` | `/api/status` calls `core.refresh_status()` before answering, so a finished download can never be advertised again |
| `linda_desktop/app.py:391-394` | `/api/models/sets`: refresh status, start a job only when something is really left to fetch **and** no job runs, return the job snapshot |
| `linda_desktop/app.py:405-411` | `/api/models/download`: if `files_to_fetch(core.manifest)` is empty → `{"status": "up_to_date"}` (200, status refreshed, no job); explicit `job.running()` → `409 err_download_running` |
| `web/index.html:2863-2864` | `lpSetupGo.disabled = dlBusy \|\| storeRequired`, where `dlBusy` covers `checking, downloading, verifying, applying, finishing` |
| `web/index.html:2845`, `web/desktop-shell.js:192` | `window.LINDA_syncModelsCta(busy)` disables the shell "Download models" CTA while a job runs |
| `web/index.html:2890` | `lpSetsApply.disabled = busy` from the same render pass |
| `web/index.html:2920-2922` | setup set cards disabled while a job runs (the choice must not change under a running job) |
| `web/index.html:2926` | `window.LINDA_downloadBusy()` — one shared phase predicate |
| `web/index.html:2930-2941` | `lpSetupGo.onclick`: refuse while busy with `err_download_running`, disable the button, re-render from `/api/status` afterwards, re-enable only when the job has ended |
| `web/index.html:2953-2963` | `lpSetsApply.onclick`: same guard, disable on entry, re-render from `/api/status`, re-enable only when the job has ended |

`web/served/index.html` is a legacy build artifact that `app.py` never reads (`config.resource_dir()/web/index.html`)
and no test or tool regenerates; it was left alone.

## Tests — `tests/test_model_sets_bug.py` (6 new, all green)

Real `fastapi.testclient.TestClient` on `create_app(Core())` against the `repo` fixture (a local HTTP repository
with a real Ed25519-signed `latest.json`), so every scenario goes through the actual endpoints.

| test | scenario |
|---|---|
| `test_second_click_while_downloading_is_refused_and_does_not_spawn_a_job` | (a) choose both on a fresh profile, press Download twice while the job is parked in `downloading`: one `_run` call, second `/api/models/download` → 409, `/api/models/sets` → 409 |
| `test_adding_lite_while_pro_is_installed_downloads_only_lite` | (b) pro installed, switch to both: only `models/linda_speed*` is fetched, `set_info` shows both installed, `weights_missing` is false afterwards |
| `test_status_is_fresh_after_download_and_a_redundant_click_does_not_redo_it` | (c)+(e) after `done`, `weights_missing` is false, `bytes_to_download` absent, both sets installed; a redundant `/api/models/download` returns 200 and fetches **zero** files |
| `test_switching_back_to_pro_removes_lite_and_shows_it_missing` | (d) back to pro: lite files deleted, `set_info['lite'].installed == False`, `weights_missing == False`; re-adding lite fetches exactly `models/linda_speed_131/model.onnx` |
| `test_download_buttons_are_guarded_while_a_job_runs` | (f) static contract: both handlers check `LINDA_downloadBusy()`, `lpSetupGo`/`lpSetsApply`/set cards/CTA are disabled from the phase |
| `test_busy_helper_covers_every_download_phase` | (f) the extracted `LINDA_downloadBusy()` predicate, executed in Node: true for `checking/downloading/verifying/applying/finishing`, false for `idle/done/error/cancelled` |

## Suite

`python -m pytest tests -q -p no:randomly` → **616 passed, 11 failed**. Baseline on the untouched tree was
610 passed / 11 failed; the difference is exactly the 6 new tests. The 11 failures are the known
environment ones (no real installer/AppX/unpacked Windows process on this machine:
`test_enterprise_review`, `test_update_restart`, `test_store_package`, `test_updater` installer-hash tests,
`test_restart_draft` write-failure) — identical set before and after the change, verified by stashing the fix.

## Commit

`fix(models): model-sets download races — single job, correct effective manifest, disabled buttons while downloading`
