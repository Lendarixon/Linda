# -*- coding: utf-8 -*-
"""Speed of the whole ensemble through the app engine on one machine. ASCII output.
    python tools/bench_speed.py cpu|cuda [full]     (LINDA_HOME must hold the installed models)"""
import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TORCH_BLAS_PREFER_HIPBLASLT", "0")
dev = sys.argv[1]
sent = "full" if "full" in sys.argv else "auto"
from linda_desktop import config, engine  # noqa: E402

engine.save_settings({"device": dev, "sentences": sent})
rows = [json.loads(l) for l in open(r"C:\Users\ninja\Desktop\детектор\data\external\hum_extra\holdout.jsonl", encoding="utf-8")]
pool = " ".join(r["text"] for r in rows if r["cohort"] == "x1_oct")


def text_of(n):
    return " ".join(pool.split()[:n])


E = engine.Engine()
t = time.time()
E.ensure_loaded()
load = time.time() - t
import torch  # noqa: E402

name = torch.cuda.get_device_name(0) if dev == "cuda" and torch.cuda.is_available() else "CPU, %d threads" % torch.get_num_threads()
print("device:", E.device, "|", name, "| sentence mode:", E.sentence_mode(), "| model load %.1f s" % load)
for n in (300, 1000, 3000):
    tx = text_of(n)
    E.run(tx, "sensitive")  # warm-up
    ts = []
    for _ in range(3):
        t = time.time()
        r = E.run(tx, "sensitive")
        ts.append(time.time() - t)
    print("%5d words: median %.2f s (min %.2f, max %.2f) | windows %d, sentences %d, verdict %s, essay %.2f" % (
        len(tx.split()), statistics.median(ts), min(ts), max(ts), r["n_windows"], r["sentence_stats"]["total"], r["verdict"], r["essay"]))
