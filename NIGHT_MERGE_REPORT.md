# NIGHT N4-B — Merge Report (night/release-2.5)

Date: 2026-11-21 · Branch: `night/release-2.5` · Base: `rc/2.4` @ `4036bc1` · No push.

## 1. Merge log

| # | Source | Commit merged | Merge commit | Result |
|---|--------|---------------|--------------|--------|
| 1 | `night/humanizer` | `d59e695` perf(humanizer): batch chunks into one padded generate() call (+2.3-3.4x on ROCm) | `0a18309` | clean, no conflicts |
| 2 | `night/pack15` | `4f1e95a` feat(tokens): RU v2 token heads in pack_15_nightly | `218026e` | clean, no conflicts |

Branch creation: `git checkout -b night/release-2.5 rc/2.4` (rc/2.4 itself untouched).

Both night branches were already descended from `rc/2.4` HEAD `4036bc1`
(`git merge-base --is-ancestor rc/2.4 <branch>` → true for both), so git's `ort`
strategy merged them without a single conflict hunk. **No manual conflict
resolution was required** — the plan's "prefer rc/2.4 side for app.py/updater.py,
keep humanize_pack.py from night/humanizer, keep voters.py lang-gate from
night/pack15" end state was reached by construction:

- `linda_desktop/app.py`, `linda_desktop/updater.py` — untouched by both merges,
  i.e. `bc37148` content preserved verbatim.
- `linda_desktop/humanize_pack.py` — from `night/humanizer` (batched `generate()`,
  `batch_chunks = 4`, `need_free` 6.0 → 2.5 for `full`). `tests/test_tool_cancellation.py`
  and new `tests/test_humanizer_batch.py` came with it.
- `linda_pro/voters.py` — from `night/pack15`: `load_token_head(model_dir, lang=None)` /
  `token_head_info(model_dir, lang=None)` select `tok_head_<lang>.npz` in shared l14
  voice dirs with fallback to `tok_head.npz`.
- `linda_desktop/engine.py` — from `night/pack15`: `TOKEN_HEADS_V2` gains
  `("essay", "ru")`, `("multi", "ru")`; both `token_head_info` / `load_token_head`
  call sites pass `lang=self.document_language(det)`.

Branches deliberately NOT merged (do not exist):
`git branch -a | grep night` → `night/humanizer`, `night/pack15` only. No
`night/lite2` / `night/lite3` present.

## 2. Pre-merge worktree hygiene

The checkout that held `night/pack15` had 2 dirty tracked files plus 3 untracked
night artefacts. The dirty `humanize_pack.py` blob hash matched `d59e695`'s blob
exactly, so the content was already committed and safe to discard.

Backed up to `%LOCALAPPDATA%/Temp/n4b_backup/` (`pack15_dirty.patch`,
`test_humanizer_batch.py`), then `git checkout --` / `rm` before branching.
Remaining untracked night reports (`HUMANIZER_REPORT_20261120.md`,
`REVIEW_*_NEON_20261120.md`, `release_prep_20261120/`, `tools/build_store_2400.py`,
`tools/site_update_2400.py`) were left uncommitted and out of this merge.

## 3. Test counts (full suite, merged branch)

venv: `C:/Users/ninja/Desktop/детектор/.venv/Scripts/python.exe`
(Python 3.13.14, pytest 9.1.1). `PYTHONPATH`/`PYTHONHOME` unset;
`LINDA_HOME`/`LINDA_MODELS_HOME` pointed at `%LOCALAPPDATA%/hermes/cache/scratch`.
CPU only, no GPU.

First full run on the merged branch — **13 failed, 660 passed (179.46 s)**:
the 12 known env failures **plus one new**:

```
tests/test_token_heads_v2.py::test_auto_keeps_context_path_for_unvalidated_pairs[essay-ru]
    AssertionError: assert 'tokens' == 'hybrid'
```

### The new failure and the fix

Not a code defect — a stale test premise. That test's parameter list included
`("essay", "ru")` with the docstring "ru has no head at all", which was true on
`rc/2.4` but is precisely what `night/pack15` changed: RU v2 heads are now
calibrated and listed in `TOKEN_HEADS_V2`, so auto markup correctly promotes
`essay/ru` to the token path. Fixed minimally in `tests/test_token_heads_v2.py`:

- dropped `("essay", "ru")` from `test_auto_keeps_context_path_for_unvalidated_pairs`
  (kept `("multi", "en")`, which is still below its all-positive ceiling);
- added `test_auto_promotes_ru_v2_heads` asserting `essay/ru` → `"tokens"`;
- updated the module docstring to match.

No production code was changed. Focused re-run
(`test_token_heads_v2.py test_humanizer_batch.py test_tool_cancellation.py`):
**35 passed (4.86 s)**.

Final full run on the merged branch — **12 failed, 660 passed (176.91 s)**:

```
FAILED tests/test_enterprise_review.py::test_download_reserved_before_thread_can_start
FAILED tests/test_enterprise_review.py::test_installer_flags_are_invisible_and_do_not_reboot
FAILED tests/test_enterprise_review.py::test_staged_installer_rechecked_before_execution
FAILED tests/test_license_api.py::test_download_through_api_and_settings
FAILED tests/test_restart_draft.py::test_restart_draft_write_failure_keeps_app_running
FAILED tests/test_store_package.py::test_real_windows_process_is_unpacked
FAILED tests/test_update_restart.py::test_staged_installer_newer_found_stale_removed
FAILED tests/test_update_restart.py::test_restart_launches_staged_installer
FAILED tests/test_update_restart.py::test_dev_rejects_production_channel_even_with_valid_signature
FAILED tests/test_update_restart.py::test_dev_accepts_only_its_signed_app_identity
FAILED tests/test_updater.py::test_app_required_and_installer_info
FAILED tests/test_updater.py::test_installer_hash_checked
```

These are the **12 pre-existing environment failures** listed verbatim in
`MERGE_RESOLUTION_REPORT.md` §3 (updater / Store packaging / installer env:
`linda_desktop.updater.UpdateError: Application updates are managed by Microsoft
Store / Windows package deployment` and relatives). Same 12 names, same order of
magnitude — **no merge-induced failures remain**.

Counts: 660 passed / 672 collected. `rc/2.4` baseline for the same venv+env was
574 passed / 12 failed; the +86 passing tests are the new humanizer batch test
module (109 lines) plus the pack15 token-head cases and pre-existing additions on
the night branches.

## 4. State

- `night/release-2.5` exists locally, contains both merges, is checked out.
- `git status` — only the pre-existing untracked night artefacts; no conflict
  markers anywhere (`git diff --name-only --diff-filter=U` → empty).
- No push. `rc/2.4` not modified. PID 18877 not touched. No GPU used.
- Verified semantically, not just by clean merge: `batch_chunks` present at
  `humanize_pack.py:372`, RU pairs present in `engine.py:664-665`, lang-aware head
  lookup present in `voters.py:85-100`.

---

# N6 — SHIP-verdict branch merges (2026-11-21)

Night N6-A folded the two SHIP-verdict branches into `night/release-2.5`.

## 1. Merges

| Branch | HEAD | Merge commit | Effect |
|---|---|---|---|
| `night/speed2` | `115b2b7` | `083e21d` | PRO ONNX graph freezes the batch axis (`static_batch`, `batch: "static1"`) — 2.55x on DirectML, verdicts identical. Touches `linda_desktop/onnx_gpu.py` + `tests/test_onnx_gpu.py` only. |
| `night/lite2` | `929585e` | `cfddcae` | Length-binned split-conformal thresholds for `SpeedOnnx` (+abstain band), resolves 5 PL false positives. New `linda_pro/speed_conformal.json`, `SpeedOnnx.load_conformal`/`conformal_verdict`, caller in `routed.py:293-295`, `tests/test_lite_conformal.py`. |
| `night/lite3` | — | — | **Not merged — branch does not exist.** `git log night/lite3` → unknown revision; no `LITE_RETRAIN_NIGHT.md` verdict file anywhere under either `tmp/night_20261121/`. Nothing to gate on, so skipped per the N6 rule. |

Both merges were clean (`ort` strategy, zero conflicts). The expected `voters.py`
collision with night/pack15's lang-gate never materialised: pack15 added
`load_token_head(model_dir, lang)` / `_head_calibration` (lines 60-100) while lite2
appended `load_conformal`/`conformal_verdict` at line 430+ — disjoint regions.
Both changes are present in the merged file, no manual resolution needed.

## 2. Test run

venv `C:/Users/ninja/Desktop/детектор/.venv/Scripts/python.exe` (pytest 9.1.1),
`PYTHONPATH`/`PYTHONHOME` unset, `pytest tests -q`, 216.12 s.

**666 passed, 11 failed, 0 collection errors.**

The 11 failures are all members of the documented pre-existing environment set
(updater / Store packaging / installer: `UpdateError: Application updates are
managed by Microsoft Store` and relatives). `test_license_api::test_download_through_api_and_settings`,
previously failing, now passes — so 666 vs the 660 of N4B, and the failure count
dropped 12 → 11. No new failure names.

## 3. State

- `night/release-2.5` checked out, both merge commits on top of `383fb8c`.
- `git status` clean apart from pre-existing untracked night artefacts.
- No push. `rc/2.4` untouched. PID 18877 untouched. CPU only.
- Spot-checked post-merge: `static_batch` present in `onnx_gpu.py:30-88` with the
  frozen batch axis, `speed_conformal.json` present with 4 bins / `abstain_margin`
  0.05, `routed.py:293` routes through `conformal_verdict`, and pack15's lang-aware
  head lookup survives at `voters.py:85-100`.
