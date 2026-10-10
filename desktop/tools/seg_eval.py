# -*- coding: utf-8 -*-
"""Проверка разметки предложений на смешанных текстах с известной границей (человек + ИИ из dev-наборов).

Собирает документы трёх видов на язык: смешанные (ЧИ, ИЧ, ЧИЧ; куски 120-450 слов, склейка по абзацам), чисто человеческие, чисто ИИ.
Для каждого предложения сохраняет долю ИИ-слов по правде и margins главного голоса набора в нескольких режимах:
  smooth   — окна ~300 слов (как Lite в 2.0.4.2), предложение = среднее накрывающих окон;
  ctxN     — предложение вместе с соседями до N слов (N = 60, 120), каждое предложение оценивается напрямую;
  single   — одно предложение;
плюс вердикт документа. Пороги подбираются потом по этому файлу (tools/seg_pick.py), без новых прогонов моделей.

    LINDA_HOME=... LINDA_MODELS_HOME=... python tools/seg_eval.py OUT.jsonl --set lite|pro [--n-mixed 40 --n-pure 20]
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import linda_desktop.engine as E  # noqa: E402
from linda_desktop.sentences import split_sentences_with_offsets  # noqa: E402

SETS = Path(r"C:\Users\ninja\Desktop\детектор\eval\sets")
SOURCES = {"en": ["essays_dev_en.jsonl", "dev_en.jsonl", "frontier_dev_en.jsonl"],
           "ru": ["dev_ru.jsonl", "essays_dev_ru.jsonl"],
           "pl": ["dev_pl.jsonl", "genre_dev_pl.jsonl"]}


def load(lang):
    hum, ai = [], []
    for f in SOURCES[lang]:
        for line in open(SETS / f, encoding="utf-8"):
            r = json.loads(line)
            if len(r["text"].split()) >= 150:
                (ai if r["label"] == "ai" else hum).append(r["text"])
    return hum, ai


def piece(text, lo, hi, rnd):
    """Начало текста от lo до hi слов, обрезанное по границе абзаца или предложения."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, n = [], 0
    target = rnd.randint(lo, hi)
    for p in paras:
        out.append(p)
        n += len(p.split())
        if n >= target:
            break
    s = "\n\n".join(out)
    if n > hi * 1.4:  # один огромный абзац: режем по предложениям
        acc, k = [], 0
        for sp in split_sentences_with_offsets(s):
            acc.append(sp.text)
            k += len(sp.text.split())
            if k >= target:
                break
        s = " ".join(acc)
    return s


def build(lang, n_mixed, n_pure, rnd):
    hum, ai = load(lang)
    rnd.shuffle(hum)
    rnd.shuffle(ai)
    docs = []
    for i in range(n_mixed):
        pat = ["HA", "AH", "HAH"][i % 3]
        parts = []
        for j, c in enumerate(pat):
            src = hum if c == "H" else ai
            parts.append((c, piece(src[(i * 3 + j) % len(src)], 120, 450, rnd)))
        docs.append(("mixed_" + pat, parts))
    for i in range(n_pure):
        docs.append(("human", [("H", piece(hum[-1 - i], 400, 1200, rnd))]))
        docs.append(("ai", [("A", piece(ai[-1 - i], 400, 1200, rnd))]))
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--set", choices=("lite", "pro"), required=True)
    ap.add_argument("--langs", default="en,ru,pl")
    ap.add_argument("--n-mixed", type=int, default=40)
    ap.add_argument("--n-pure", type=int, default=20)
    a = ap.parse_args()
    rnd = random.Random(7)
    E.load_settings = lambda: {"sentences": "smooth", "quality": a.set, "model_sets": [a.set], "device": "cpu" if a.set == "lite" else "dml"}
    eng = E.Engine()
    out = open(a.out, "w", encoding="utf-8")
    for lang in a.langs.split(","):
        for kind, parts in build(lang, a.n_mixed, a.n_pure, rnd):
            text = "\n\n".join(t for _, t in parts)
            # правда по символам: какие куски ИИ
            spans, pos = [], 0
            for c, t in parts:
                st = text.index(t, pos)
                spans.append((st, st + len(t), c))
                pos = st + len(t)
            res = eng.run(text, mode="sensitive")
            det = eng.ensure_for_language(res.get("language") or lang)["sensitive"]
            sents = split_sentences_with_offsets(text)
            stexts = [s.text for s in sents]
            from linda_pro.voters import clean_text
            modes = {"smooth": [x["essay_margin"] for x in res["sentences"]]}
            fe, fm = det._factory("linda_essay"), det._factory("linda_multi_v2")
            facs = [("", fe)] + ([("_m", fm)] if fm is not fe else [])  # у Pro вторая модель (Multi) — свои margins
            if len(facs) > 1:
                modes["smooth_m"] = [x["multi_margin"] for x in res["sentences"]]
            for suf, fac in facs:
                modes["single" + suf] = [float(v) for v in fac.margins(stexts)]
                for cw in (60, 120):
                    eng.CONTEXT_WORDS = cw
                    _, ctx = eng._sentence_contexts(stexts, 10 ** 6)  # каждое предложение напрямую
                    modes[f"ctx{cw}{suf}"] = [float(v) for v in fac.margins([clean_text(t) for t in ctx])]
            eng.CONTEXT_WORDS = 120
            rows = []
            for i, s in enumerate(sents):
                w = max(1, len(s.text.split()))
                ai_chars = sum(max(0, min(s.end, b) - max(s.start, a0)) for a0, b, c in spans if c == "A")
                rows.append({"w": w, "ai": round(ai_chars / max(1, s.end - s.start), 3), **{m: round(v[i], 4) for m, v in modes.items()}})
            out.write(json.dumps({"lang": lang, "set": a.set, "kind": kind, "verdict": res["verdict"], "essay": res.get("essay"),
                                  "tier": getattr(eng, "tier", None), "sents": rows}) + "\n")
            out.flush()
    print("done", flush=True)


if __name__ == "__main__":
    main()
