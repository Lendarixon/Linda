# -*- coding: utf-8 -*-
"""Проверка Linda-Pro на ВАШИХ размеченных текстах.
    python evaluate.py --human folder_of_human_txt --ai folder_of_ai_txt [--mode sensitive|precise]
    python evaluate.py --jsonl labelled.jsonl        # строки {"text": ..., "label": "human"|"ai"}
Пишет evaluation_report.csv; данные никуда не отправляются."""
import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from linda_pro import LindaPro  # noqa: E402


def auroc(y, s):
    y, s = np.asarray(y), np.asarray(s, float)
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    for v in np.unique(s):  # средние ранги при равных оценках
        m = s == v
        ranks[m] = ranks[m].mean()
    n1, n0 = y.sum(), (1 - y).sum()
    return float((ranks[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--human")
    ap.add_argument("--ai")
    ap.add_argument("--jsonl")
    ap.add_argument("--mode", choices=["sensitive", "precise"], default="sensitive")
    ap.add_argument("--min-words", type=int, default=100)
    a = ap.parse_args()
    items = []
    if a.jsonl:
        for l in open(a.jsonl, encoding="utf-8"):
            r = json.loads(l)
            items.append((r["text"], 1 if r["label"] == "ai" else 0, str(len(items))))
    else:
        for folder, lab in ((a.human, 0), (a.ai, 1)):
            for f in sorted(Path(folder).glob("*.txt")):
                items.append((f.read_text(encoding="utf-8", errors="replace"), lab, f.name))
    items = [x for x in items if len(x[0].split()) >= a.min_words]
    y = [x[1] for x in items]
    if sum(y) < 5 or len(y) - sum(y) < 5:
        sys.exit("need at least 5 texts of each class (recommended 100+), >= %d words each" % a.min_words)
    res = LindaPro(mode=a.mode).detect([x[0] for x in items])
    ens = [r["ens_z"] for r in res]
    ess = [r["essay"] for r in res]
    ver = [r["verdict"] for r in res]
    y = np.array(y)
    print(f"texts: {len(y)} (human {int((y == 0).sum())}, ai {int(y.sum())}); mode {a.mode}")
    print(f"AUROC essay-score {auroc(y, ess):.3f}; ensemble-score {auroc(y, ens):.3f}")
    for name, pos in (("ai", lambda v: v == "ai"), ("ai or uncertain", lambda v: v != "human")):
        p = np.array([pos(v) for v in ver])
        print(f"verdict '{name}': true-positive rate {100 * p[y == 1].mean():.1f}%, false-positive rate {100 * p[y == 0].mean():.1f}%")
    with open("evaluation_report.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "label", "verdict", "essay_score", "ensemble_z", "ai_share", "n_windows"])
        for (t, lab, i), r in zip(items, res):
            w.writerow([i, "ai" if lab else "human", r["verdict"], f"{r['essay']:.3f}", f"{r['ens_z']:.3f}", f"{r['ai_share']:.2f}", r["n_windows"]])
    print("wrote evaluation_report.csv")


if __name__ == "__main__":
    main()
