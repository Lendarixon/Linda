# -*- coding: utf-8 -*-
"""P4b: measure real VRAM of the Essay fp32 DML graph with Windows GPU Adapter Memory counters.

onnxruntime DirectML memory is invisible to HIP/torch counters, so the device-wide
"Dedicated Usage" counter (same numbers Task Manager shows) is sampled at three points:
baseline, after the session is created, and after a forward pass. The session is kept
alive while each sample is taken.

    "C:/Users/ninja/Desktop/сикс севен/.venv-rocm101/Scripts/python.exe" tools/night_2501_p4_vram_dml.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:/Linda_2100_Dev")
WORK = ROOT / "work/night_2501"
GRAPH = WORK / "vram/onnx/essay_fp32/model.onnx"
MAXLEN = 256
PS1 = WORK / "gpu_proc_mem.ps1"


def gpu_usage() -> dict:
    """counter-name -> bytes for THIS process, sampled by work/night_2501/gpu_proc_mem.ps1.

    DirectML allocations never appear in HIP/torch counters, so the Windows GPU
    performance counters (what Task Manager shows) are the device-truth source.
    """
    p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                        "-TargetPid", str(os.getpid()), "-Rounds", "3"],
                       capture_output=True, text=True, timeout=120)
    out = {}
    for line in p.stdout.splitlines():
        if "=" in line:
            k, _, v = line.strip().partition("=")
            try:
                out[k] = int(v)
            except ValueError:
                pass
    return out


def main() -> int:
    import numpy as np
    import onnxruntime as ort

    assert GRAPH.is_file(), f"missing graph {GRAPH}"
    res = {"graph": str(GRAPH), "graph_mb": round(GRAPH.stat().st_size / 1e6, 1), "max_len": MAXLEN,
           "adapter": "AMD Radeon RX 9070 XT (16 GB)", "source": "Windows GPU Process Memory counter (this pid)"}

    base1 = gpu_usage()
    time.sleep(0.5)
    base2 = gpu_usage()
    base = {k: min(base1.get(k, 0), base2.get(k, 0)) for k in set(base1) | set(base2)}
    res["baseline_bytes"] = base

    so = ort.SessionOptions()
    so.log_severity_level = 3
    t0 = time.time()
    sess = ort.InferenceSession(str(GRAPH), sess_options=so,
                                providers=["DmlExecutionProvider", "CPUExecutionProvider"])
    res["load_seconds"] = round(time.time() - t0, 1)
    res["provider_used"] = sess.get_providers()[0]
    time.sleep(0.6)
    after_load = gpu_usage()

    ids = np.random.default_rng(0).integers(0, 1000, size=(1, MAXLEN), dtype=np.int64)
    ids[0, 0] = 1
    mask = np.ones((1, MAXLEN), dtype=np.int64)
    mask[0, MAXLEN // 2:] = 0
    t0 = time.time()
    logits = sess.run(["logits"], {"input_ids": ids, "attention_mask": mask})[0]
    first = round((time.time() - t0) * 1000, 1)
    t0 = time.time()
    for _ in range(5):
        sess.run(["logits"], {"input_ids": ids, "attention_mask": mask})
    warm = round((time.time() - t0) / 5 * 1000, 1)
    time.sleep(0.4)
    after_fwd = gpu_usage()

    lg = logits.astype(np.float32).ravel().tolist()
    p_ai = 1 / (1 + np.exp(-(lg[1] - lg[0]))) if len(lg) >= 2 else None
    res["forward"] = {"shape": list(logits.shape), "logits": [round(x, 4) for x in lg],
                      "p_ai": round(float(p_ai), 4) if p_ai is not None else None,
                      "first_ms": first, "warm_ms": warm}

    def delta(after: dict) -> dict:
        d = {}
        for k, v in after.items():
            dv = v - base.get(k, 0)
            if dv > 32 * 2**20:  # ignore noise under 32 MB
                d[k] = {"base_mb": round(base.get(k, 0) / 2**20, 1),
                        "now_mb": round(v / 2**20, 1), "delta_mb": round(dv / 2**20, 1)}
        return d

    res["after_load"] = delta(after_load)
    res["after_forward"] = delta(after_fwd)
    biggest = max([v["delta_mb"] for v in res["after_forward"].values()], default=0.0)
    res["vram_used_mb"] = round(biggest, 1)
    res["vram_used_gb"] = round(biggest / 1024, 2)
    res["under_4gb"] = bool(biggest / 1024 <= 4.0)
    del sess
    (WORK / "p4_vram_dml.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
