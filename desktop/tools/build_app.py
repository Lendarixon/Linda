"""Build only the isolated Dev executable; no production paths or signing material."""
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
os.environ.update(OMP_NUM_THREADS='6', MKL_NUM_THREADS='6', OPENBLAS_NUM_THREADS='6')
args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--name', 'Linda-Pro', '--noconsole', '--onedir',
        '--distpath', str(root/'dist'), '--workpath', str(root/'build'), '--specpath', str(root/'build'),
        '--icon', str(root/'assets/linda.ico')]
for relative in ('web', 'assets', 'linda_desktop/data', 'linda_pro/_vendor/aidetector/patterns'):
    args += ['--add-data', f'{root/relative};{relative}']
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
