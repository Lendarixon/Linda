# -*- coding: utf-8 -*-
"""Разметка Pro на смешанных текстах (файл tools/seg_eval.py --set pro): p предложения = среднее сигмоид Essay и Multi, как в движке.
Печатает текущие пороги и лучшие альтернативы по режимам hybrid (max(одно предложение, контекст 120)) и context (контекст 120).
    python tools/seg_pick_pro.py seg_pro.jsonl ROUTING.json"""
import json
import math
import sys
from collections import defaultdict


def sig(x, c, s):
    return 1 / (1 + math.exp(-max(-30, min(30, (x - c) / s))))


T = json.load(open(sys.argv[2], encoding="utf-8"))
docs = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]


def probs(d, mode):
    h = T["languages"][d["lang"]]["tiers"]["full"]["heat"]
    pe = (h["essay"]["thr_5"], max(1e-3, (h["essay"]["thr_05"] - h["essay"]["thr_5"]) / 2))
    pm = (h["multi"]["thr_5"], max(1e-3, (h["multi"]["thr_05"] - h["multi"]["thr_5"]) / 2))
    out = []
    for r in d["sents"]:
        if mode == "hybrid":
            e, m = max(r["single"], r["ctx120"]), max(r["single_m"], r["ctx120_m"])
        else:
            e, m = r[mode], r[mode + "_m"]
        out.append((sig(e, *pe) + sig(m, *pm)) / 2)
    return out


def ev(mode, ta, tu):
    acc = defaultdict(float)
    bnd = []
    raised = nh = 0
    for d in docs:
        wa = tot = 0
        for r, p in zip(d["sents"], probs(d, mode)):
            lab = "ai" if p >= ta else "unc" if p >= tu else "hum"
            tr = "A" if r["ai"] >= 0.5 else "H"
            acc[tr + lab] += r["w"]
            acc[tr] += r["w"]
            tot += r["w"]
            wa += r["w"] * (lab == "ai")
            if d["kind"].startswith("mixed"):
                bnd.append((tr == "A") == (lab == "ai"))
        if d["kind"] == "human":
            nh += 1
            raised += wa / tot >= 0.25
    return acc["Hai"] / acc["H"], acc["Hunc"] / acc["H"], acc["Aai"] / acc["A"], acc["Aunc"] / acc["A"], sum(bnd) / len(bnd), raised, nh


def show(mode, ta, tu, tag=""):
    h, hu, a, au, b, r, n = ev(mode, ta, tu)
    print(f"{mode:7s} ai>={ta:.2f} unc>={tu:.2f}: human words ai {h:.3f} unc {hu:.3f} | AI words ai {a:.3f} unc {au:.3f} | mixed acc {b:.3f} | human docs >=25% ai {r}/{n} {tag}")


print("docs", len(docs))
show("hybrid", 0.72, 0.45, "<- сейчас (<=1500 слов)")
show("ctx120", 0.58, 0.38, "<- сейчас (длинные тексты)")
for mode in ("hybrid", "ctx120", "ctx60"):
    best = None
    for ta in [x / 100 for x in range(40, 96, 2)]:
        h, hu, a, au, b, r, n = ev(mode, ta, 0.3)
        if h <= 0.03 and (best is None or a > best[1]):
            best = (ta, a)
    if best:
        for tu in (0.3, 0.4, 0.5):
            show(mode, best[0], tu, "<- лучший при <=3% человеческих слов «ИИ»")
