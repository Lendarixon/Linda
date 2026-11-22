# BUG1_MODELS_2501 — «Обновить модели»: 32 МБ → 0% → кнопка возвращается

Branch `night/fix-2.5.0.1`, base HEAD `729be4a`. Files: `linda_desktop/updater.py`, `linda_desktop/app.py`, `web/index.html`, `tests/test_models_2501.py`.

## Root cause (2 independent defects, both needed for the symptom)

1. **`files_to_fetch()` trusted the installed manifest's own hash.** When the installer reused the old 1.3.4.1 profile, the leftover
   `manifest.json` still listed the *new* hashes for the big files (`path` + `size` + `sha256` all equal to latest.json). The cheap
   check `p.is_file() and size == f["size"]` plus `old[path]["sha256"] == f["sha256"]` → "present, skip". So
   `bytes_to_download` = only the genuinely new small files (the reported **32 MB**), while ~3 GB of stale bytes stayed on disk.
   The job then re-verified/`_apply_staged` those files against the *lying* record and either failed the checksum or finished over
   bad files, and `is_complete()` (size-only) then reported "complete" → banner flipped back to the button.
2. **The banner had no branch for a failed/stopped model job** (`web/index.html`, `else if (d.phase === 'error')` existed only for
   *installer* jobs). A failed weights download fell through to `weights_update → btn_models`, i.e. visually "reverts to button"
   with no error text — exactly what the owner saw.

Secondary: the parallel downloader's progress was `done["bytes"] += f["size"]` computed only **after** each whole file finished,
and `_download_to` reported `done_before + got` per worker — with 4 workers each starting from its own base and the aggregate
resetting, the bar sat at 0% (or jumped to 50%/100% at file boundaries). Progress never reflected bytes actually fetched.

## Reproduction (offline, CPU, stub signed server)

Scratch repros (stub Ed25519 repo + fake reused root) showed on unpatched HEAD:

| scenario | before | after |
|---|---|---|
| reused 1.3.4.1, same paths+sha, 8 new small files | `bytes_to_download` = 5.5 MB, job "done" over stale bytes | full set re-hashed, stale file re-downloaded, `done == total` |
| version bump, byte-identical files | `files_to_fetch` = 0 → `/api/models/download` answered `up_to_date`, button dead | job adopts the version, `installed_version` = new, banner clears |
| 2×220 MB parallel download | progress 0% → 50% → 100% (no in-file granularity) | monotonic 0→100%, max observed 100%, 0 backwards steps |
| downloader writes nothing, claims success | phase `done`, `is_complete` False, button back | phase `error` ("checksum mismatch / incomplete"), no false done |

On the owner's real leftover profile (`%LOCALAPPDATA%\Linda-Pro-2500`, 34 files, 2.97 GB): `files_to_fetch(verify=True)` → 0 stale
files in 1.7 s (the reuse really is byte-identical there, so the fix is a no-op for that profile — the 32 MB job was the *trust*
path, and it would have failed only when bytes differed).

## Fix

- `updater.files_to_fetch(manifest, root, verify=None, progress=None)` — `verify=None` now means **re-hash whenever the installed
  version differs from the manifest version**; a successful hash is cached in a `.ok` marker so the expensive pass runs once.
  `progress(done, total)` drives the UI during hashing.
- `updater.update_status()` — `bytes_to_download` / new `files_to_download` come from `_estimate_download()`, an honest **floor**
  (no gigabyte hashing on the status poll); never a bogus 0 for a moved version.
- `Job._run()` — verifies with `verify=True`; sets `phase="checking"` with live progress while hashing; `total = sum(todo)`; if
  `is_complete()` is still false at the end it raises `UpdateError("... still incomplete ...")` instead of reporting `done`.
- `Job._add_fetched()` — one shared, monotonic, clamped-to-total counter fed by every chunk (`_download_to`) and by resumed `.part`
  bytes; parallel workers no longer race or reset it.
- `app.py /api/models/download` — when the cheap pass finds nothing but `weights_update` is true, re-hashes; if truly nothing is
  missing it starts the job so the version is adopted, instead of answering `up_to_date` forever.
- `web/index.html` — new banner branches for `download.phase == 'error'` / `'cancelled'` (message + Retry), i18n keys
  `banner_models_failed` / `banner_models_stopped` in en/pl/ru.

`is_complete()` deliberately stays size-only: it runs on every `/api/status` poll and must not hash 3 GB.

## Tests — `tests/test_models_2501.py` (5 new, 13 in file, all pass)

- `test_reused_install_same_size_different_bytes_is_refetched` — reproduces the trust bug (`verify=False` skips the big file) and
  asserts the default path catches it.
- `test_update_status_does_not_promise_zero_bytes_for_a_reused_install`
- `test_job_progress_moves_and_ends_at_100_percent` — monotonic samples, partial bytes seen, `done == total`, stale file replaced.
- `test_job_never_reports_done_with_files_missing` — phase `error`, never `done`.
- `test_version_bump_with_identical_files_still_applies` — reuse-only bump adopts the version.

Output: `python -m pytest tests/test_models_2501.py -q` → **13 passed in 3.07s**.

Regression run (`test_models_2501, test_model_sets, test_model_sets_bug, test_auto_models, test_models_location,
test_update_pipeline_20261121, test_reuse_2501, test_installer_2501, test_updater, test_ui_update_review`) → **79 passed, 3 failed**;
all three (`test_model_sets::test_adding_and_removing_a_set`, `test_updater::test_app_required_and_installer_info`,
`test_updater::test_installer_hash_checked`) fail identically on the stashed baseline `729be4a` — pre-existing, unrelated
(APP_VERSION > fake 9.0.0 / set-removal dir cleanup / installer hash fixture).

No push. No GPU, no network beyond 127.0.0.1 stub servers.
