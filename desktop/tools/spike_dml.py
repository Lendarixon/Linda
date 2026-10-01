# -*- coding: utf-8 -*-
"""Spike: ONNX + DirectML on this PC versus the torch CPU path of the shipped package. ASCII output."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from linda_desktop import onnx_gpu
from linda_pro.voters import FastSeqCls

MODELS = Path(r"C:\Users\ninja\Desktop\hf_upload\Linda-Pro-1.1\models")
CACHE = Path(r"C:\Users\ninja\Desktop\Linda_desktop\_onnx_cache")
rows = [json.loads(l) for l in open(r"C:\Users\ninja\Desktop\детектор\data\external\hum_extra\holdout.jsonl", encoding="utf-8")]
ai = [r["text"] for r in rows if r["cohort"] == "x1_oct"][:4]
hum = []
for l in open(r"C:\Users\ninja\Desktop\детектор\eval\sets\essays_en.jsonl", encoding="utf-8"):
    r = json.loads(l)
    if r.get("label") in (0, "human"):
        hum.append(r["text"])
    if len(hum) >= 4:
        break
texts = ai + hum + [" ".join(ai[0].split()[:40]), ai[1] + " " + ai[2] + " " + hum[0]]  # short, long, mixed
print("texts:", len(texts), "| words:", [len(t.split()) for t in texts])
print("DML available:", onnx_gpu.available())
for name in ("linda_multi_d", "linda_essay_d"):
    d = MODELS / name
    ref = FastSeqCls(d, batch=8, device="cpu")
    t0 = time.time(); zr = np.array(ref.margins(texts)); t_ref = time.time() - t0
    og = onnx_gpu.OnnxSeqCls(d, CACHE)
    t0 = time.time(); og._load(); t_load = time.time() - t0
    t0 = time.time(); zo = np.array(og.margins(texts)); t_run = time.time() - t0
    t0 = time.time(); zo2 = np.array(og.margins(texts)); t_run2 = time.time() - t0
    print("%s: export+load %.0f s | torch CPU %.1f s | DirectML first %.1f s, second %.1f s" % (name, t_load, t_ref, t_run, t_run2))
    print("   max |diff| %.3f, mean |diff| %.3f | torch %s" % (np.abs(zr - zo2).max(), np.abs(zr - zo2).mean(), np.round(zr, 2).tolist()))
    print("   dml   %s" % np.round(zo2, 2).tolist())
    print("   sign agreement:", int(((zr > 0) == (zo2 > 0)).sum()), "/", len(zr))
