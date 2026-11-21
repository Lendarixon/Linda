from __future__ import annotations

import json
import os
import sys
from pathlib import Path

APP_NAME = 'Linda Trace'
APP_VERSION = '1.3.0'
BUNDLED_MODEL_VERSION = '1.0.0'
APP_ID = '{CE0B5225-A593-484F-9277-7507D7707252}'
HF_REPO = 'Lindarixon/Linda-Trace'
GITHUB_REPO = 'Lendarixon/Linda-Trace'
SITE_URL = 'https://lendarixon.github.io/Linda-Trace/'
RELEASES_URL = f'https://github.com/{GITHUB_REPO}/releases'
BASE_URL = os.environ.get('TRACE_BASE_URL', f'https://huggingface.co/{HF_REPO}/resolve/main').rstrip('/')
MANIFEST_NAME = 'latest.json'
SIGNATURE_NAME = 'latest.json.sig'
SIGNING_PUBKEY_B64 = os.environ.get('TRACE_PUBKEY_B64', '1uPfXe1IO9egH/t+j0hAqzneMdtT8tmqaLSRcFnIe0E=')
BASE_DIR = Path(__file__).resolve().parent
MODEL_FILES = ('char_ngrams_model.json',)

DEEPTRACE_MODEL_NAME = 'linda_master_style_head.ts'


def data_root() -> Path:
    """Return the current application data root."""
    override = os.environ.get('FORENSIC_DATA_ROOT')
    if override:
        return Path(override)
    if getattr(sys, 'frozen', False):
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ForensicAuthorship'
    return BASE_DIR


def models_root() -> Path:
    """Return the Trace update storage directory."""
    return data_root() / 'trace_update'


def get_deeptrace_dir() -> Path:
    """Return the active directory for Linda DeepTrace neural weights."""
    override = os.environ.get('LINDA_DEEPTRACE_DIR')
    if override and Path(override).exists():
        return Path(override)
    
    settings_file = data_root() / 'deeptrace_settings.json'
    if settings_file.is_file():
        try:
            cfg = json.loads(settings_file.read_text(encoding='utf-8'))
            custom_p = cfg.get('custom_dir')
            if custom_p and Path(custom_p).exists():
                return Path(custom_p)
        except Exception:
            pass
            
    # Default search locations:
    # 1. Next to executable / project root in deeptrace/
    local_dt = BASE_DIR / 'deeptrace'
    if (local_dt / DEEPTRACE_MODEL_NAME).is_file():
        return local_dt
        
    # 2. In %LOCALAPPDATA%/ForensicAuthorship/deeptrace
    app_dt = data_root() / 'deeptrace'
    return app_dt


def is_deeptrace_installed() -> bool:
    """Check if the DeepTrace model weights file exists in the configured directory."""
    dt_dir = get_deeptrace_dir()
    return (dt_dir / DEEPTRACE_MODEL_NAME).is_file()


def set_deeptrace_dir(path_str: str) -> None:
    """Save custom directory for DeepTrace in settings."""
    settings_file = data_root() / 'deeptrace_settings.json'
    cfg = {}
    if settings_file.is_file():
        try:
            cfg = json.loads(settings_file.read_text(encoding='utf-8'))
        except Exception:
            pass
    cfg['custom_dir'] = str(path_str)
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    settings_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')


_GPU_CACHE: dict | None = None


def detect_gpu_info(force_refresh: bool = False) -> dict:
    """Detect available graphics accelerators. Computed once and cached.

    Runs without a console flash (CREATE_NO_WINDOW on Windows). CPU is the
    default and only supported device: AMD CUDA is unavailable, so
    'recommended' is always False. Text: «Работает на процессоре».
    """
    global _GPU_CACHE
    if _GPU_CACHE is not None and not force_refresh:
        return dict(_GPU_CACHE)
    info = {'has_gpu': False, 'name': 'Не обнаружена', 'recommended': False,
            'device': 'cpu', 'note': 'Работает на процессоре'}
    try:
        import subprocess
        cmd = ['powershell', '-NoProfile', '-Command',
               'Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name']
        kwargs: dict = {'capture_output': True, 'text': True, 'timeout': 4}
        if sys.platform == 'win32':
            kwargs['creationflags'] = 0x08000000  # CREATE_NO_WINDOW: no console flash
        p = subprocess.run(cmd, **kwargs)
        if p.returncode == 0 and p.stdout.strip():
            names = [line.strip() for line in p.stdout.splitlines() if line.strip()]
            # Keep the name for display, but never recommend GPU: CPU-only build.
            if names:
                info['has_gpu'] = True
                info['name'] = names[0]
                info['recommended'] = False
    except Exception:
        pass
    _GPU_CACHE = dict(info)
    return dict(info)


def deeptrace_status() -> dict:
    """Honest DeepTrace readiness: no_weights | no_base | no_runtime | ready.

    Guarantees state == 'ready' ONLY when extraction can actually execute.
    If the base model is absent or transformer runtime libraries are missing,
    reports 'no_base' or 'no_runtime' accordingly, never a false 'ready'.
    """
    dt_dir = get_deeptrace_dir()
    ts_head = (dt_dir / DEEPTRACE_MODEL_NAME).is_file()
    onnx_candidates = [
        dt_dir / 'linda_master_style_head.onnx',
        dt_dir / 'linda_master_style_head.int8.onnx',
        BASE_DIR / 'deeptrace' / 'linda_master_style_head.onnx',
        BASE_DIR / 'deeptrace' / 'linda_master_style_head.int8.onnx',
    ]
    onnx_head = any(c.is_file() for c in onnx_candidates)
    weights_ok = ts_head or onnx_head

    base_dir = BASE_DIR / 'models' / 'xlm-roberta-base'
    base_ok = base_dir.is_dir() and any(base_dir.iterdir())

    has_ort = False
    has_torch = False
    has_transformers = False
    try:
        import onnxruntime  # noqa: F401
        has_ort = True
    except Exception:
        pass
    try:
        import torch  # noqa: F401
        has_torch = True
    except Exception:
        pass
    try:
        import transformers  # noqa: F401
        has_transformers = True
    except Exception:
        pass

    # Extraction requires base model + transformers + (torch or (onnxruntime and onnx_head))
    can_extract = weights_ok and base_ok and has_transformers and (has_torch or (has_ort and onnx_head))

    runtime_label = None
    if has_ort and onnx_head and has_transformers:
        runtime_label = 'onnxruntime'
    elif has_torch and has_transformers:
        runtime_label = 'torch'
    elif has_ort:
        runtime_label = 'onnxruntime'
    elif has_torch:
        runtime_label = 'torch'

    if not weights_ok:
        state = 'no_weights'
    elif not base_ok:
        state = 'no_base'
    elif not can_extract:
        state = 'no_runtime'
    else:
        state = 'ready'

    gpu = detect_gpu_info()
    return {
        'state': state,
        'installed': state == 'ready',
        'weights_present': weights_ok,
        'base_present': base_ok,
        'runtime': runtime_label,
        'directory': str(dt_dir),
        'device': 'cpu',
        'note': 'Работает на процессоре',
        'gpu_info': gpu
    }
