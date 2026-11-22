# INSTALLER_ISSUES_2500

## Fixer 1 (models/updater) — 2.5.0.1, branch night/fix-2.5.0.1

Root causes and fixes:

- (B) Stale bundled models: tools/release_2400.py copies the whole base `_internal` (which can carry an old
  models payload from a 1.3.4.1-era build) straight into the installer; nothing strips models from the bundle.
  Fix: installer bundles NO models — [Files] ships only the app; models come exclusively from the signed live
  latest.json on first run. installer/linda.iss already writes installer_choice.json from the chosen radio
  (lite/pro/both, incl. /MODELSET= for silent installs) via SaveSetsChoice; verified in source.
- (D) "Update models" 0% then reverts: update_status() computed bytes_to_download only when
  weights_update/weights_missing, and files_to_fetch()/is_complete() compared against the RAW installed manifest,
  so a lean set-split latest.json (61 files) vs an old 34-file 1.3.4.1 manifest or a partial install yielded
  bytes_to_download=0 / weights_missing=False and the job exited instantly. Fix: all three now use the EFFECTIVE
  (selected-sets) manifest; bytes_to_download > 0 whenever weights_update/weights_missing is true.
- (E-partial) Uninstall: linda.iss [Uninstall] deletes models/onnx/calibration/staging and DataDir only after an
  explicit YES on the "UninstallModels" prompt; %LOCALAPPDATA% profiles are NOT deleted by default. No change needed.

Tests: tests/test_models_2501.py (5 tests: files_to_fetch vs old 34-file manifest, partial install,
update_status bytes>0 on weights_update, weights_missing partial, is_complete effective-vs-raw). 5 passed.
