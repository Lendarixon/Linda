# Backend Review Fixes — Neon review 2026-11-20 (rc/2.4)

| Review item | Fix (file:line) | Test |
|---|---|---|
| P0: `/api/trace/corpora*` missing license guard | `linda_desktop/app.py` — `check_licensed("trace")` + `terr("err_need_license", 403)` added to all 4 handlers (`trace_corpora_list`, `trace_corpora_get`, `trace_corpora_save`, `trace_corpora_delete`) | `test_trace_corpora_routes_refuse_without_license`, `test_trace_corpora_routes_pass_gate_when_licensed` |
| P1: TOCTOU in `/api/packs/download` | `linda_desktop/packs.py` new `try_start()` (check-and-set under `_pack_lock`); `app.py` `packs_download` uses it | `test_packs_try_start_is_atomic`, `test_packs_download_refuses_concurrent_other_pack` |
| P1: unlocked `job_snapshot()` read | `linda_desktop/packs.py` — `return dict(_pack_job)` under `_pack_lock` | `test_packs_job_snapshot_returns_copy_under_lock` |
| P1: `ensure_runtime` unlocked + generate vs unload race | `linda_desktop/humanize_pack.py` — module-level `_runtime_lock` (RLock) around `ensure_runtime`; `gen()` grabs backend ref + sets `_backend_busy` under lock, releases during generation; `unload()` refuses while busy | `test_humanize_unload_refused_while_generating`, `test_humanize_ensure_runtime_serialized` |
| P1: `SpeedOnnx.token_scores` crash on mmBERT | `linda_pro/voters.py:597` — `cls_id, sep_id, pad_id = self._special(...)` after special-token lookup | `test_speed_onnx_token_scores_uses_special_ids` |
| P1: fail-open on corrupt `expires_at` | `linda_desktop/licensing.py:246-249` — unparseable `expires_at` ⇒ not licensed (fail-closed), exempt in dev mode | `test_licensing_fail_closed_on_corrupt_expires_at`, `test_licensing_dev_mode_keeps_fail_open` |

Tests: `tests/test_backend_review_fixes.py` (10 tests, all pass). Full suite: 652 passed, 12 failed — all 12 are pre-existing environment failures (Store-package/updater tests), identical before and after these changes.
