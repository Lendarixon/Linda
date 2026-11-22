# VERIFY_2501 — independent verification of night/fix-2.5.0.1 (65552b7)

Branch: night/fix-2.5.0.1 @ 65552b7ed9fd224823e4b062aef669e7663727b2
Date: 2026-11-22 (UTC+1). Verifier: independent subagent, CPU only, no push.

## 1. Tests — PASS (with 2 pre-existing env failures, not from this commit)
`env -u PYTHONPATH -u PYTHONHOME python -m pytest tests/test_models_2501.py tests/test_updater.py -q`
→ **16 passed, 2 failed** in 11.79s. All 5 of tests/test_models_2501.py PASS.
The 2 failures (test_app_required_and_installer_info, test_installer_hash_checked) fail because
`config.is_store_package()` is true in this shell (packaged env), so `download_installer` raises
"managed by Microsoft Store". Reproduced identical failure on parent commit 70a9f21 → pre-existing,
environment-caused, NOT introduced by 65552b7.

## 2. "Update models 0% then reverts" repro vs NEW code — PASS (bug not reproduced)
Fake profile: LINDA_HOME/LINDA_MODELS_HOME, old 1.3.4.1 manifest (34 files), only 10 present, no .ok markers,
settings model_sets=[pro]. Stub HTTP server (127.0.0.1:8471) serving signed lean 61-file latest.json
(25 pro + 16 lite + 20 shared, ed25519-signed, LINDA_PUBKEY_B64 override).
- get_manifest() → effective manifest (pro+shared = 45 files)
- update_status: weights_update=True, weights_missing=True, **bytes_to_download=26000 > 0**
- files_to_fetch: 45 of 45
- simulated download loop: phase 0% → 3.8% → 88.5% → 100% (monotonic, ends at 1.0)
- after apply (manifest.json replaced): weights_update=False, weights_missing=False → up_to-date
PASS: bytes>0, phase advances, button reaches up-to-date. Old code would have reported bytes_to_download=0.

## 3. Installer bundles no models — PASS
dist/Linda-Pro contains only Linda-Pro.exe; no _internal/models, no manifest, no calibration/onnx.
tools/repack_exe.py: no models references. tools/release_2400.py copies BASE/_internal wholesale
(line 107) — bundle is clean because the base _internal carries no models payload; models come only
from signed live latest.json at first run. No change needed.
installer/linda.iss: not touched (owned by parallel worker).

## Verdict: PASS — ship 2.5.0.1. No code changes required.
