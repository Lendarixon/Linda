# -*- coding: utf-8 -*-
"""P4: GPU VRAM smoke on the RX 9070 XT via the ROCm 10.1 venv.

Loads the Essay ONNX (fp32) at the production shape, runs one forward, and reports
VRAM from rocm-smi (plus torch's own hip counter as a cross-check).

    "C:/Users/ninja/Desktop/сикс севен/.venv-rocm101/Scripts/python.exe" tools/night_2501_p4_vram.py
"""
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r'D:/Linda_2100_Dev')
WORK = ROOT / 'work/night_2501'
SRC = Path(r'C:/Users/ninja/Desktop/детектор')          # torch/onnxruntime live here
OUT = WORK / 'vram'
MAXLEN = 256                                             # production window (speed_args / train_args)


def rocm_free_used():
    """(used_mb, total_mb) for the first GPU.

    rocm-smi is not installed on this host, so the device-wide figure comes from
    HIP via torch.cuda.mem_get_info(), which reports actual free/total VRAM.
    """
    try:
        import torch
        if torch.cuda.is_available():
            free, total = torch.cuda.mem_get_info()
            return (total - free) / 2**20, total / 2**20
    except Exception:  # noqa: BLE001
        pass
    exe = shutil.which('rocm-smi') or r'C:/Program Files/AMD/ROCm/6.2/bin/rocm-smi.exe'
    for cmd in ([exe, '--showmeminfo', 'vram', '--json'], [exe, '--showmeminfo', 'vram']):
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            continue
        if p.returncode != 0:
            continue
        txt = p.stdout
        try:
            j = json.loads(txt)
            for card, info in j.items():
                used = None
                total = None
                for k, v in info.items():
                    kl = k.lower()
                    if 'used' in kl:
                        used = int(v)
                    if 'total' in kl:
                        total = int(v)
                if used is not None and total:
                    return used / 1024 / 1024, total / 1024 / 1024
        except (ValueError, KeyError, AttributeError):
            import re
            vals = [int(x) for x in re.findall(r'(\d{6,})', txt)]
            if len(vals) >= 2:
                return max(vals) / 1024 / 1024, 0
    return None, None


def torch_hip_mem():
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        torch.cuda.synchronize()
        return {'allocated_mb': round(torch.cuda.memory_allocated() / 2**20, 1),
                'reserved_mb': round(torch.cuda.memory_reserved() / 2**20, 1),
                'peak_mb': round(torch.cuda.max_memory_allocated() / 2**20, 1)}
    except Exception as e:  # noqa: BLE001
        return {'error': f'{type(e).__name__}: {e}'}


def main() -> int:
    os.environ.pop('PYTHONPATH', None)
    os.environ.pop('PYTHONHOME', None)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(SRC))
    OUT.mkdir(parents=True, exist_ok=True)
    res = {'stage': 'start'}
    try:
        import onnxruntime as ort
        import torch
    except Exception as e:  # noqa: BLE001
        res['error'] = f'{type(e).__name__}: {e}'
        print(json.dumps(res, indent=1))
        return 1

    res['torch'] = {'version': torch.__version__, 'hip': getattr(torch.version, 'hip', None),
                    'cuda_available': torch.cuda.is_available(),
                    'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    res['ort'] = {'version': ort.__version__, 'providers': ort.get_available_providers()}

    model_dir = ROOT / 'qa_models/models/essay_dhi_131_20261008'
    cache = OUT / 'onnx'
    target = cache / 'essay_fp32' / 'model.onnx'
    res['model_dir'] = str(model_dir)
    res['onnx'] = str(target)

    used0, total = rocm_free_used()
    res['vram_before'] = {'used_mb': round(used0, 1) if used0 else None, 'total_mb': round(total, 1) if total else None}

    # --- build the fp32 ONNX at the production shape if it is not there yet ---
    if not target.is_file():
        res['stage'] = 'export'
        from linda_desktop import onnx_gpu
        t0 = time.time()
        p = onnx_gpu.export(model_dir, cache / 'essay_fp32', MAXLEN, fp16=False, tokens=False, static_batch=True)
        res['export_seconds'] = round(time.time() - t0, 1)
        res['export_size_mb'] = round(p.stat().st_size / 1e6, 1)
        target = p
    else:
        res['export_size_mb'] = round(target.stat().st_size / 1e6, 1)
        res['export_seconds'] = 0

    # --- load + one forward on the GPU ---
    res['stage'] = 'load'
    providers = [p for p in ('ROCMExecutionProvider', 'CUDAExecutionProvider', 'DmlExecutionProvider')
                 if p in ort.get_available_providers()]
    res['providers_used'] = providers or ['CPUExecutionProvider']
    so = ort.SessionOptions()
    so.log_severity_level = 3
    t0 = time.time()
    sess = ort.InferenceSession(str(target), sess_options=so, providers=res['providers_used'])
    res['load_seconds'] = round(time.time() - t0, 1)

    res['stage'] = 'forward'
    import numpy as np
    rng = np.random.default_rng(0)
    ids = rng.integers(0, 1000, size=(1, MAXLEN), dtype=np.int64)
    ids[0, 0] = 1
    mask = np.ones((1, MAXLEN), dtype=np.int64)
    mask[0, MAXLEN // 2:] = 0                       # a realistic half-padded window
    t0 = time.time()
    out = sess.run(['logits'], {'input_ids': ids, 'attention_mask': mask})
    first = round(time.time() - t0, 3)
    t0 = time.time()
    for _ in range(5):
        sess.run(['logits'], {'input_ids': ids, 'attention_mask': mask})
    warm = round((time.time() - t0) / 5, 3)
    logits = out[0].ravel().tolist()
    p_ai = 1 / (1 + math.exp(-(logits[1] - logits[0]))) if len(logits) >= 2 else None
    res['forward'] = {'shape': list(out[0].shape), 'logits': [round(x, 4) for x in logits],
                      'p_ai': round(p_ai, 4) if p_ai is not None else None,
                      'first_ms': int(first * 1000), 'warm_ms': int(warm * 1000), 'max_len': MAXLEN}

    used1, _ = rocm_free_used()
    res['vram_after'] = {'used_mb': round(used1, 1) if used1 else None}
    delta = (used1 - used0) if (used0 and used1) else None
    res['vram_used_mb'] = round(delta, 1) if delta is not None else None
    res['vram_used_gb'] = round(delta / 1024, 2) if delta is not None else None
    res['torch_hip_mem'] = torch_hip_mem()
    res['target_ok'] = bool(delta is not None and delta / 1024 <= 4.0)
    res['stage'] = 'done'

    (WORK / 'p4_vram.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(res, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
