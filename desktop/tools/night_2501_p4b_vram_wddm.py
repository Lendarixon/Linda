# -*- coding: utf-8 -*-
"""P4b: measure the DirectML session's real VRAM footprint via the Windows
'GPU Process Memory' performance counters (the D3D12/WDDM allocation path that
DirectML actually uses — HIP counters cannot see it).

Samples the current process's Dedicated + Shared usage before load, after load and
after a production-shape forward, at 200 ms granularity, so the peak is caught.

    "C:/Users/ninja/Desktop/сикс севен/.venv-rocm101/Scripts/python.exe" tools/night_2501_p4b_vram_wddm.py
"""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(r'D:/Linda_2100_Dev')
WORK = ROOT / 'work/night_2501'
SRC = Path(r'C:/Users/ninja/Desktop/детектор')
OUT = WORK / 'vram'
MAXLEN = 256

PS = ('$ErrorActionPreference="SilentlyContinue";'
      '$s=Get-Counter -Counter "\\GPU Process Memory(pid_{pid}*)\\Dedicated Usage",'
      '"\\GPU Process Memory(pid_{pid}*)\\Shared Usage" -MaxSamples 1;'
      '$d=($s.CounterSamples|?{{$_.Path -like "*Dedicated*"}}|Measure-Object -Property CookedValue -Sum).Sum;'
      '$h=($s.CounterSamples|?{{$_.Path -like "*Shared*"}}|Measure-Object -Property CookedValue -Sum).Sum;'
      'Write-Output ("{{0}} {{1}}" -f [int64]$d,[int64]$h)')


def sample(pid: int) -> tuple[int, int] | None:
    try:
        p = subprocess.run(['powershell', '-NoProfile', '-Command', PS.format(pid=pid)],
                           capture_output=True, text=True, timeout=40)
        parts = p.stdout.split()
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return None


class Sampler(threading.Thread):
    def __init__(self, pid):
        super().__init__(daemon=True)
        self.pid, self.stop, self.samples = pid, threading.Event(), []

    def run(self):
        while not self.stop.is_set():
            s = sample(self.pid)
            if s:
                self.samples.append((round(time.time(), 2), s[0], s[1]))
            time.sleep(0.2)

    def peak(self):
        if not self.samples:
            return None
        return {'dedicated_mb': round(max(s[1] for s in self.samples) / 2**20, 1),
                'shared_mb': round(max(s[2] for s in self.samples) / 2**20, 1),
                'n_samples': len(self.samples)}


def main() -> int:
    os.environ.pop('PYTHONPATH', None)
    os.environ.pop('PYTHONHOME', None)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(SRC))
    OUT.mkdir(parents=True, exist_ok=True)
    res = {'stage': 'start', 'pid': os.getpid()}

    import numpy as np
    import onnxruntime as ort
    import torch

    res['torch'] = {'version': torch.__version__, 'hip': getattr(torch.version, 'hip', None),
                    'device': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}
    res['ort'] = {'version': ort.__version__, 'providers': ort.get_available_providers()}

    target = OUT / 'onnx' / 'essay_fp32' / 'model.onnx'
    if not target.is_file():
        res['error'] = 'onnx not built; run night_2501_p4_vram.py first'
        print(json.dumps(res, indent=1))
        return 1
    res['onnx'] = str(target)
    res['onnx_size_mb'] = round(target.stat().st_size / 1e6, 1)

    s = Sampler(os.getpid())
    s.start()
    time.sleep(2.5)
    base = sample(os.getpid())
    res['baseline'] = {'dedicated_mb': round(base[0] / 2**20, 1), 'shared_mb': round(base[1] / 2**20, 1)} if base else None

    so = ort.SessionOptions()
    so.log_severity_level = 3
    provs = [p for p in ('ROCMExecutionProvider', 'CUDAExecutionProvider', 'DmlExecutionProvider')
             if p in ort.get_available_providers()] or ['CPUExecutionProvider']
    res['providers_used'] = provs
    t0 = time.time()
    sess = ort.InferenceSession(str(target), sess_options=so, providers=provs)
    res['load_seconds'] = round(time.time() - t0, 1)
    time.sleep(2.5)
    after_load = sample(os.getpid())
    res['after_load'] = {'dedicated_mb': round(after_load[0] / 2**20, 1),
                        'shared_mb': round(after_load[1] / 2**20, 1)} if after_load else None

    rng = np.random.default_rng(7)
    ids = rng.integers(0, 1000, size=(1, MAXLEN), dtype=np.int64)
    ids[0, 0] = 1
    mask = np.ones((1, MAXLEN), dtype=np.int64)
    mask[0, MAXLEN // 2:] = 0
    t0 = time.time()
    out = sess.run(['logits'], {'input_ids': ids, 'attention_mask': mask})
    first = round(time.time() - t0, 3)
    t0 = time.time()
    for _ in range(5):
        sess.run(['logits'], {'input_ids': ids, 'attention_mask': mask})
    warm = round((time.time() - t0) / 5, 3)
    time.sleep(1.5)
    after_run = sample(os.getpid())
    s.stop.set()
    s.join(timeout=5)

    logits = out[0].ravel().tolist()
    import math
    p_ai = 1 / (1 + math.exp(-(logits[1] - logits[0]))) if len(logits) >= 2 else None
    res['forward'] = {'shape': list(out[0].shape), 'logits': [round(x, 4) for x in logits],
                      'p_ai': round(p_ai, 4) if p_ai is not None else None,
                      'first_ms': int(first * 1000), 'warm_ms': int(warm * 1000), 'max_len': MAXLEN}
    res['after_run'] = {'dedicated_mb': round(after_run[0] / 2**20, 1),
                       'shared_mb': round(after_run[1] / 2**20, 1)} if after_run else None
    res['peak'] = s.peak()
    if res['peak'] and res['baseline']:
        res['process_vram_gb'] = round(res['peak']['dedicated_mb'] / 1024, 2)
        res['delta_vs_baseline_gb'] = round((res['peak']['dedicated_mb'] - res['baseline']['dedicated_mb']) / 1024, 2)
    res['hip_device_total_mb'] = round(torch.cuda.mem_get_info()[1] / 2**20, 0) if torch.cuda.is_available() else None
    res['target_ok'] = bool(res.get('process_vram_gb') is not None and res['process_vram_gb'] <= 4.0)
    res['stage'] = 'done'

    (WORK / 'p4b_vram.json').write_text(json.dumps(res, indent=1), encoding='utf-8')
    print(json.dumps(res, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
