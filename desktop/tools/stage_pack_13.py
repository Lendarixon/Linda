# -*- coding: utf-8 -*-
"""Пакет моделей 1.3 (merged D25/H25/I50): models/, onnx/, calibration/routing.json. Жёсткие ссылки, ничего не копируется лишний раз.
    python tools/stage_pack_13.py OUT_DIR"""
import json, os, shutil, sys
from pathlib import Path
RES = Path(r"C:\Users\ninja\Desktop\детектор")
CAND = Path(r"C:\Users\ninja\Desktop\Linda_1.3_beta_candidate\artifacts\model_pack_1_3_beta")
VOICES = ("essay_dhi_25_25_50_20261005", "multi_dhi_25_25_50_20261005")
out = Path(sys.argv[1]); shutil.rmtree(out, ignore_errors=True)
def link(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    try: os.link(src, dst)
    except OSError: shutil.copy2(src, dst)
def tree(src, dst, skip=()):
    for p in src.rglob("*"):
        if p.is_file() and p.name not in skip: link(p, dst / p.relative_to(src))
for v in VOICES:
    tree(RES / "models/experimental" / v, out / "models" / v, skip=("merge_report.json", "train_args.json"))
    tree(RES / "models/experimental/merged_onnx_20261005" / v, out / "onnx" / v)
tree(CAND / "models/stylo_d", out / "models/stylo_d")
(out / "calibration").mkdir(parents=True)
shutil.copy2(RES / "eval/reports/routing_merged.json", out / "calibration/routing.json")
print("ok", sum(f.stat().st_size for f in out.rglob("*") if f.is_file()) / 2**30, "GiB")
