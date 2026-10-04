"""Build only the isolated Dev executable; no production paths or signing material."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
core_root = root if (root/'linda_pro').is_dir() else root.parent
if not (core_root/'linda_pro').is_dir():
    raise SystemExit('Missing linda_pro core source')
os.environ.update(OMP_NUM_THREADS='6', MKL_NUM_THREADS='6', OPENBLAS_NUM_THREADS='6')
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--name', 'Linda-Pro', '--noconsole', '--onedir',
        '--distpath', str(root/'dist'), '--workpath', str(root/'build'), '--specpath', str(root/'build'),
        '--paths', str(core_root), '--icon', str(root/'assets/linda.ico'), '--manifest', str(root/'assets/windows-runtime.manifest')]
for relative in ('web', 'assets', 'linda_desktop/data'):
    args += ['--add-data', f'{root/relative};{relative}']
args += ['--add-data', f'{core_root/"linda_pro/_vendor/aidetector/patterns"};linda_pro/_vendor/aidetector/patterns']
parser = root/'assets/document-parser'
if not (parser/'Linda-Document-Worker.exe').is_file():
    raise SystemExit('Build the secure document parser before building the application')
for module in ('uvicorn','linda_pro','linda_desktop','transformers.models.deberta_v2','transformers.models.deberta','onnx'):
    args += ['--collect-submodules', module]
for module in ('webview','lightgbm','pythonnet','onnxruntime'):
    args += ['--collect-all',module]
for module in ('onnx','fpdf','sklearn.feature_extraction.text','sklearn.preprocessing','scipy.sparse','tiktoken_ext.openai_public','tiktoken_ext','multipart'):
    args += ['--hidden-import',module]
for module in ('matplotlib','tkinter','IPython','pytest'):
    args += ['--exclude-module',module]
for package in ('tqdm','regex','requests','packaging','filelock','numpy','tokenizers','safetensors','huggingface_hub','torch','onnx','onnxruntime-directml','transformers','pyyaml','python-docx','pypdf','fpdf2','fastapi','starlette','pydantic','uvicorn'):
    args += ['--copy-metadata',package]
args.append(str(root/'run_app.py'))
raise SystemExit(subprocess.call(args, cwd=root))
