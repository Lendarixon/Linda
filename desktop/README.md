# Linda-Pro desktop app (Windows)

Local app around the Linda-Pro detector: first start downloads the model files from Hugging Face (about 2.9 GB, once), then everything runs offline.
Colour map of the text, sensitive / precise modes, CPU or GPU, licence key dialog, update check (signed manifest) for models and for the app itself.

* `linda_desktop/` - local web backend (FastAPI on 127.0.0.1), update logic (`updater.py`), licence (`licensing.py`), engine (`engine.py`), window launcher (`__main__.py`)
* `web/index.html` - the UI (built by `tools/make_web.py`)
* `installer/linda.iss` - Inno Setup script (per-user install, silent update switches)
* `tools/` - build, signing of the update manifest (`make_manifest.py`), test helpers

Build (Python 3.12): `pip install torch --index-url https://download.pytorch.org/whl/cpu`, `pip install -r requirements.txt` (see the imports), copy the `linda_pro/` package next to `run_app.py`,
`python tools/build_app.py`, then compile `installer/linda.iss` with Inno Setup. Tests: `python -m pytest tests`.

Updates: the app reads `latest.json` and `latest.json.sig` from the Hugging Face repository; the Ed25519 signature must verify with the public key in `linda_desktop/config.py`
and every file hash is checked. The signing key is not part of this repository.

Licence of the code: see the repository `LICENSE` (free for non-commercial use; commercial use needs a key).
