# FINISH_2501.md — Linda 2.5.0.1 Final Build & Verification

## Build Summary
- **Branch:** `night/fix-2.5.0.1`
- **Toolchain:** Python `3.12.10` (`tools/release_2501.py`), Inno Setup `6.7.3` (`ISCC.exe`)
- **Output folder:** `C:/Users/ninja/Desktop/Linda_2.5.0.1/`
  - `app/Linda-Pro.exe`: `79,046,145` bytes, SHA-256 `1c28489c6b1dc25f70786828887b1edddd638ff54f100213a085274fe1014164`
  - `Linda-Setup.exe`: `509,274,156` bytes, SHA-256 `532301d3f7659966135d6833686c252f14798d4934d76b76dd8843040e9e22aa`
  - `SHA256.json`, `Linda-Setup.exe.sha256`, `app/Linda-Pro.exe.sha256`

## Runtime Bug Fixes (2.5.0.1)
1. **HF missing `calibration/routing.with_lite.json` (404 on startup download):**
   - Uploaded `C:/Users/ninja/Desktop/детектор/tmp/night_20261121/pack_15_nightly/calibration/routing.with_lite.json` (8,596 B, SHA-256 `d9052577c494dd7485c85cb5f3e224a1c875454071a8319597bb4bcdc0eaa008`) to `Lindarixon/Linda-Pro` `main` in commit `63dfa63304218b1414efe30461988d3aacb39f95`.
   - Verified via `curl.exe -sIL` / download: `HTTP/1.1 200 OK`, `Content-Length: 8596`, SHA-256 `d9052577c494dd7485c85cb5f3e224a1c875454071a8319597bb4bcdc0eaa008`.
   - **`linda_desktop/updater.py`:** HTTP 404 for optional paths (`_is_optional_entry`, matching `routing.with_lite.json`) is logged and recorded in `skipped_optional.json` / `Job.state["skipped_optional"]` + `warning` instead of failing the whole download; non-optional 404s still raise `UpdateError` naming the missing file.
   - **`linda_desktop/engine.py`:** `routing_with_lite_file()` falls back to `calibration/routing.json` with a warning when `routing.with_lite.json` is missing; `calibration_file()` excludes `routing.with_lite.json` and `token_heads_v2.json`.
   - **`tests/test_models_2501.py`:** Added tests for optional `routing.with_lite.json` 404 skip + warning, required 404 failure naming the file, and `Engine.routing_with_lite_file()` fallback.
2. **Reinstall-Reuse across Profile Directories (`installer/linda.iss`):**
   - Added `FindSavedModels`, `ReadModelsPath`, `ParseVerSeg`, `CompareVersionStr`, and `ConsiderSavedModelsCandidate`: scans `DataDir`, `%LOCALAPPDATA%\Linda-Pro*\` (`models_location.json` + `manifest.json`), and `%LOCALAPPDATA%\Packages\*Linda*\LocalState\` (`models_location.json` + `manifest.json`), preferring profiles with model dirs on disk and picking the newest manifest version.
   - Defaults `ModelsPage` to the discovered `SavedModelsPath`, preselects `SetsPage.SelectedValueIndex`, renders green `ReuseFound` banner (`SetsReuseNote`) in `english`, `russian`, and `polish`, and writes `reuse_models`, `reuse_version`, and `reuse_sets` into `installer_choice.json` when path and set match.
   - **`linda_desktop/updater.py`:** `selected_sets()` honors `reuse_models` when the saved `manifest.json` version matches `reuse_version`, while preserving explicit `settings.json` `model_sets` overrides.
   - **`tests/test_reuse_2501.py`:** Updated `.iss` assertions for `FindSavedModels`, `Linda-Pro*`, `Packages`/`LocalState`, and `CompareVersionStr`.
3. **Access-Denied Fix on Upgrade/Reinstall (`installer/linda.iss`):**
   - Set `CloseApplications=force` in `[Setup]`.
   - Added `FindProcessesByName`, `EnumWindowsCloseProc`, and `CloseRunningLindaProcesses` in `[Code]` (invoked from `PrepareToInstall` and `CurStepChanged(ssInstall)`): snapshots processes via `CreateToolhelp32Snapshot`, skips `GetCurrentProcessId`, sends `WM_CLOSE` via `EnumWindows` and waits up to 3s, then calls `OpenProcess` + `TerminateProcess` for any remaining `Linda-Pro.exe` PIDs, with a hidden `taskkill.exe /F /IM Linda-Pro.exe` (`SW_HIDE`) fallback.

## Verification Results
- **Pytest (2501 + routing + pipeline suites):** `tests/test_models_2501.py` + `tests/test_installer_2501.py` + `tests/test_reuse_2501.py` + `tests/test_startup_2100.py` + `tests/test_lang_routing_13beta.py` + `tests/test_merged_routing.py` + `tests/test_update_pipeline_20261121.py` → **60 passed** (`32` + `28`).
- **Silent Install Over Running Instance Proof:** Started old installed `C:/Users/ninja/AppData/Local/Programs/Linda-Pro/Linda-Pro.exe --no-ui` (with 13 total `Linda-Pro.exe` PIDs active), ran `Linda-Setup.exe /SILENT /SUPPRESSMSGBOXES /DIR=%TMP%\l251kill` → exit code `0`, no access-denied errors, `CloseRunningLindaProcesses` closed/terminated all 13 PIDs (`remaining Linda-Pro.exe count=0`); started `%TMP%\l251kill\Linda-Pro.exe --no-ui` → `curl.exe` returned `HTTP 200 http://127.0.0.1:55821/`; cleaned up temp artifacts.
- **Standalone EXE (`app/Linda-Pro.exe --no-ui`):** `instance.json` created, `http://127.0.0.1:63221/` returned **HTTP 200** (`has_2501=True`).
- **Screenshot:** `work/shots_2501/reuse_note_other_profile.png` captured from `Linda-Setup.exe /CURRENTUSER /LANG=english` with fake `%LOCALAPPDATA%\Linda-Pro-FakeTest\models_location.json` → `D:\Linda_2100_Dev\tmp\fake_saved_models` (`v1.5.0`), showing preselected `Both` and green `ReuseFound` banner (also verified detecting real `Linda-Pro-2500` `v1.3.4.1`).
- **Note on HF root vs `latest.json`:** Per single-file HF write constraint, only `calibration/routing.with_lite.json` was uploaded to HF `main`. Note that live `latest.json` still references other files currently present under `packs/1.5.0-nightly/` (e.g., `calibration/token_heads_v2.json`, `models/linda_speed_131/speed_conformal.json`, `models/essay_l14m50/*`, `models/multi_l14m50/*`) that are not yet at HF `main` root.
