# -*- coding: utf-8 -*-
"""Подбор режима и порогов разметки по файлу tools/seg_eval.py (без моделей).

Вероятность предложения = сигмоида от margin (центр — порог 5% ложных у документа, ширина — половина расстояния до порога 0,5%),
как в движке. Метрики по словам: у человеческих слов доля «ИИ» и «ИИ или возможно», у ИИ-слов то же (полнота); граница — доля
слов смешанных документов с правильной меткой при пороге «ИИ»; чистые люди — доля документов, где «ИИ» >= 25% слов
(правило согласованности подняло бы вердикт до «неясно»).
    python tools/seg_pick.py seg.jsonl ROUTING.json [--fp 0.03]
"""
import argparse
import json
import math
from collections import defaultdict


def sig(x, c, s):
    return 1 / (1 + math.exp(-max(-30, min(30, (x - c) / s))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("seg")
    ap.add_argument("routing")
    ap.add_argument("--fp", type=float, default=0.03, help="предел доли человеческих слов с меткой «ИИ»")
    a = ap.parse_args()
    T = json.load(open(a.routing, encoding="utf-8"))
    docs = [json.loads(l) for l in open(a.seg, encoding="utf-8")]
    tier = "speed" if docs[0]["tier"] == "speed" else "full"
    modes = [k for k in docs[0]["sents"][0] if k not in ("w", "ai")] + ["hybrid", "smooth_ctx"]

    def probs(d, m):
        h = T["languages"][d["lang"]]["tiers"][tier]["heat"]["essay"]
        c, s = h["thr_5"], max(1e-3, (h["thr_05"] - h["thr_5"]) / 2)
        out = []
        for r in d["sents"]:
            if m == "hybrid":
                v = max(r["single"], r["ctx120"])
            elif m == "smooth_ctx":
                v = (r["smooth"] + r["ctx120"]) / 2
            else:
                v = r[m]
            out.append(sig(v, c, s))
        return out

    P = {m: [probs(d, m) for d in docs] for m in modes}
    print(f"docs={len(docs)} tier={tier} kinds={dict((k, sum(d['kind'] == k for d in docs)) for k in set(d['kind'] for d in docs))}")
    best = []
    for m in modes:
        for ta in [x / 100 for x in range(40, 96, 2)]:
            for tu in [x / 100 for x in range(20, 80, 5)]:
                if tu >= ta:
                    continue
                acc = defaultdict(float)
                per_lang = defaultdict(lambda: defaultdict(float))
                raise_h = n_h = 0
                for d, ps in zip(docs, P[m]):
                    wa = 0
                    tot = 0
                    for r, p in zip(d["sents"], ps):
                        lab = "ai" if p >= ta else "unc" if p >= tu else "hum"
                        truth = "A" if r["ai"] >= 0.5 else "H"
                        for key in (acc, per_lang[d["lang"]]):
                            key[truth + "_w"] += r["w"]
                            key[truth + "_" + lab] += r["w"]
                        tot += r["w"]
                        wa += r["w"] if lab == "ai" else 0
                    if d["kind"] == "human":
                        n_h += 1
                        raise_h += wa / max(1, tot) >= 0.25
                fp = acc["H_ai"] / acc["H_w"]
                if fp > a.fp or max(v["H_ai"] / max(1, v["H_w"]) for v in per_lang.values()) > a.fp * 1.7:
                    continue
                rec = acc["A_ai"] / acc["A_w"]
                rec_any = (acc["A_ai"] + acc["A_unc"]) / acc["A_w"]
                fp_any = (acc["H_ai"] + acc["H_unc"]) / acc["H_w"]
                best.append((rec, m, ta, tu, fp, fp_any, rec_any, raise_h / max(1, n_h),
                             {lg: round(v["A_ai"] / max(1, v["A_w"]), 2) for lg, v in per_lang.items()}))
    best.sort(key=lambda x: -x[0])
    seen = set()
    print("rec_ai  mode        ai   unc  | hum->ai hum->ai|unc  ai->ai|unc  human_docs_raised  rec_ai by lang")
    for b in best:
        if b[1] in seen:
            continue
        seen.add(b[1])
        print(f"{b[0]:.3f}  {b[1]:10s} {b[2]:.2f} {b[3]:.2f} | {b[4]:.3f}   {b[5]:.3f}        {b[6]:.3f}      {b[7]:.3f}            {b[8]}")


if __name__ == "__main__":
    main()
