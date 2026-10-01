# -*- coding: utf-8 -*-
"""Builds the Windows application folder dist/Linda-Pro with PyInstaller (no console window).
    python tools/build_app.py"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--name", "Linda-Pro", "--noconsole", "--onedir",
        "--icon", str(ROOT / "assets" / "linda.ico"),
        "--add-data", f"{ROOT / 'web'};web",
        "--add-data", f"{ROOT / 'linda_pro' / '_vendor' / 'aidetector' / 'patterns'};linda_pro/_vendor/aidetector/patterns",
        "--collect-submodules", "uvicorn", "--collect-submodules", "linda_pro", "--collect-submodules", "linda_desktop",
        "--collect-submodules", "transformers.models.deberta_v2", "--collect-submodules", "transformers.models.deberta",
        "--collect-all", "webview", "--collect-all", "lightgbm", "--collect-all", "pythonnet",
        "--hidden-import", "sklearn.feature_extraction.text", "--hidden-import", "sklearn.preprocessing", "--hidden-import", "scipy.sparse",
        "--hidden-import", "tiktoken_ext.openai_public", "--hidden-import", "tiktoken_ext", "--hidden-import", "multipart",
        "--exclude-module", "matplotlib", "--exclude-module", "tkinter", "--exclude-module", "IPython", "--exclude-module", "pytest",
        ]
for pkg in ("tqdm", "regex", "requests", "packaging", "filelock", "numpy", "tokenizers", "safetensors", "huggingface_hub", "torch", "transformers", "pyyaml", "python-docx", "pypdf", "fastapi", "starlette", "pydantic", "uvicorn"):
    args += ["--copy-metadata", pkg]
args.append(str(ROOT / "run_app.py"))
sys.exit(subprocess.call(args, cwd=ROOT))
