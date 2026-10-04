# Linda-Pro desktop app (Windows)

Local app around the Linda-Pro detector: first start downloads the model files from Hugging Face (about 2.9 GB, once), then everything runs offline.
GPU acceleration on any DirectX 12 card (AMD Radeon, NVIDIA GeForce, Intel Arc) through ONNX Runtime DirectML (`onnx_gpu.py`: the models are exported to ONNX once on the user's PC), colour map of the text, sensitive / precise modes, CPU or GPU, licence key dialog, update check (signed manifest) for models and for the app itself.

* `linda_desktop/` - local web backend (FastAPI on 127.0.0.1), update logic (`updater.py`), licence (`licensing.py`), engine (`engine.py`), window launcher (`__main__.py`);
  1.2: local history with folders (`history.py`, SQLite in the app data folder), text analytics (`analytics.py`), text structure view (`structure.py`, reference in `data/structure_ref.npz`)
* `web/index.html` - the main UI (built by `tools/make_web.py`); `web/cabinet.html` - history, batch check, document comparison, reader (added to the page by the backend)
* `installer/linda.iss` - Inno Setup script (per-user install, silent update switches)
* `tools/` - build, signing of the update manifest (`make_manifest.py`), test helpers

Build (Python 3.12): `pip install torch --index-url https://download.pytorch.org/whl/cpu`, `pip install -r requirements.txt` (see the imports), copy the `linda_pro/` package next to `run_app.py`,
`python tools/build_document_parser.py`, then `python tools/build_app.py`, then compile `installer/linda.iss` with Inno Setup. Tests: `python -m pytest tests`.

Updates: the app reads `latest.json` and `latest.json.sig` from the Hugging Face repository; the Ed25519 signature must verify with the public key in `linda_desktop/config.py`
and every file hash is checked. The signing key is not part of this repository.

Licence of the code: see the repository `LICENSE` (free for non-commercial use; commercial use needs a key).

## 1.2.1 (2026-10-03)

Colour map fix: sentences are scored alone and in their context (about 120 words) and the higher score counts ("hybrid" mode), so an AI text is no longer shown as human sentence by sentence; AI / possibly-AI thresholds are sent by the program (`sentence_stats.thresholds`). Models unchanged.

## 1.2 (2026-10-02)

History with folders (kept only on the PC; can be switched off or cleaned up automatically), batch check of any number of files, comparison of two documents with their shared passages or of many documents (overlap matrix), full reader for any saved check, authorship verdict (human / mixed / AI with shares), text analytics and a text-structure view, every sentence scored on its own with a lower "possibly AI" band, Metro animations.


## 2.0.2.20 (2026-10-04)

See [full release notes](RELEASE_NOTES_2.0.2.20.md). History and drafts now use current-user Windows DPAPI. PDF/DOCX parsing uses the bundled LPAC helper with network/file restrictions and Job limits. The audit ledger uses chained HMAC and retention; clearing is disabled. WebView2 restores its rendering surface after minimization without reloading the page. The EXE includes PerMonitorV2 and long-path support.

Build the dedicated document parser before packaging the desktop app. The generated `assets/document-parser` runtime is included in the installer, not committed to source. Model weights, signing keys and user profiles are never part of the public desktop source.
