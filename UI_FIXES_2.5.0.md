# UI_FIXES_2.5.0 — post-launch fixes, branch night/release-2.5

Commits (local, no push): `8e7a032` (version bump), `5708ff2` (updater speed), `7751a0e` (UI fixes).

## 1. Version 2.4.0.0 → 2.5.0.0
- `linda_desktop/__init__.py:2` — `__version__ = "2.5.0.0"` (drives UI/API/About via `config.APP_VERSION`).
- `linda_desktop/data/CHANGELOG.json` — new 2.5.0.0 entry (en/pl/ru), existing schema.
- `installer/linda.iss:17` — `AppVersion "2.5.0.0"` (file is gitignored; edited on disk).
- `web/served/index.html` — `window.LINDA_APP_VERSION='2.5.0.0'`.
- Note: the running exe's file-properties version is stamped at build time; it will still read 2.4.0.0 until the owner rebuilds. UI/About/API version comes from `__version__` and is already 2.5.0.0. Rebuild required for: exe resource version, installer.

## 2. Header version label removed
- `web/index.html:1061` — removed the `__LINDA_VERSION__` span next to the logo (also in `web/served/index.html`). Startup splash version kept (not the header). i18n keys untouched; `tests/test_ui_localization_contract.py` passes.

## 3. OS window title cleaned
- `linda_desktop/__main__.py:270` — `webview.create_window(config.APP_NAME.replace('Linda-Pro','Linda'), ...)` — title is now just "Linda", no version.

## 4. Logo dark box fixed
- `web/index.html:1061` (+ `web/served/index.html`) — removed the solid `<rect width="100" height="100" fill="#1ba1e2"/>` background from the brand SVG; the flag bars now sit directly on the header background.

## 5. Slow model download — diagnosis & fix (`linda_desktop/updater.py`, commit 5708ff2)
Diagnosis: up to **3 full sha256 passes** over all model files per start (`files_to_fetch`, `_verify_staged`, `_apply_staged`), and downloads strictly **serial** (one file at a time). CHUNK was already 1 MiB; resume via `.part`+Range was already correct.
Fix: `<file>.ok` marker ("<sha256> <size>") written after verify/apply — all three passes skip re-hashing when the marker matches (fall back to full hash if absent/tampered); downloads now run up to **4 files in parallel** (ThreadPoolExecutor).
Measured locally: sha256 of 8 MiB = 4.31 ms vs `.ok` check = 1.02 ms (~4× per file; on multi-GB weights the saving is seconds ×3 passes per start). New test `test_ok_marker_skips_rehash_and_download_completes` (local http.server, 100 KB file) passes; 11 updater tests pass, 2 failures pre-existing on clean tree (verified via git stash).

## Tests
- `tests/test_ui_localization_contract.py`, `tests/test_startup_2100.py` (16 passed), `tests/test_updater.py` — 31 passed, 2 pre-existing failures.
- grep: no `2.4.0.0` remains in UI-visible strings (only CHANGELOG history / tools / evidence artifacts).
