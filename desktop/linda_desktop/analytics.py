# -*- coding: utf-8 -*-
"""Extra text analytics shown next to the verdict and used by the batch / compare views. Pure Python, no models, works offline (EN / RU / PL)."""
from __future__ import annotations

import math
import re
from collections import Counter

_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
# connectives and stock transitions that are over-represented in LLM prose (a weak, explainable signal; not used in the verdict)
_STOCK = [
    "moreover", "furthermore", "additionally", "in conclusion", "overall", "it is important to note", "it is worth noting", "plays a crucial role",
    "plays a pivotal role", "delve", "tapestry", "in today's", "navigate the", "a testament to", "in the realm of", "not only", "ensure that",
    "кроме того", "более того", "таким образом", "в заключение", "важно отметить", "следует отметить", "играет ключевую роль", "играет важную роль",
    "в современном мире", "в целом", "стоит отметить", "необходимо подчеркнуть",
    "ponadto", "co więcej", "podsumowując", "warto zauważyć", "odgrywa kluczową rolę", "w dzisiejszym świecie", "należy podkreślić",
]


def words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _mattr(ws: list[str], window: int = 50) -> float:
    """Moving-average type/token ratio: lexical diversity that does not depend on text length."""
    if len(ws) < window:
        return len(set(ws)) / len(ws) if ws else 0.0
    step = max(1, (len(ws) - window) // 40)
    vals = [len(set(ws[i:i + window])) / window for i in range(0, len(ws) - window + 1, step)]
    return sum(vals) / len(vals)


def shingles(text: str, n: int = 5) -> set[tuple[str, ...]]:
    ws = words(text)
    return {tuple(ws[i:i + n]) for i in range(max(0, len(ws) - n + 1))}


def analyze(text: str, sentences: list[dict] | None = None) -> dict:
    ws = words(text)
    sents = sentences or []
    if sents:
        lengths = [len(s['text'].split()) for s in sents]
    else:
        from .sentences import split_sentences_with_offsets
        lengths = [len(s.text.split()) for s in split_sentences_with_offsets(text)]
    lens = lengths or [len(text.split())]
    mean = sum(lens) / len(lens)
    sd = math.sqrt(sum((x - mean) ** 2 for x in lens) / len(lens)) if len(lens) > 1 else 0.0
    low = text.lower()
    stock = {k: low.count(k) for k in _STOCK if low.count(k)}
    tri = Counter(tuple(ws[i:i + 3]) for i in range(max(0, len(ws) - 2)))
    rep = [(" ".join(k), v) for k, v in tri.most_common(40) if v >= 3 and len(set(k)) > 1 and sum(len(w) for w in k) >= 10][:6]
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = {
        "words": len(text.split()), "sentences": len(lengths), "paragraphs": len(paragraphs),
        "avg_sentence_words": round(mean, 1), "sentence_length_sd": round(sd, 1),
        "burstiness": round(sd / mean, 2) if mean else 0.0,      # human prose varies sentence length more (higher = more varied)
        "lexical_diversity": round(_mattr(ws), 3),                 # MATTR-50
        "avg_word_len": round(sum(map(len, ws)) / len(ws), 2) if ws else 0.0,
        "stock_phrases": sorted(stock.items(), key=lambda kv: -kv[1])[:8],
        "stock_per_1000": round(sum(stock.values()) / max(1, len(ws)) * 1000, 1),
        "repeated_phrases": rep,
    }
    if sents:
        p = [s["p_ai"] for s in sents]
        run = best = 0
        for s in sents:
            run = run + 1 if s["label"] == "ai" else 0
            best = max(best, run)
        out["longest_ai_streak"] = best
        out["top_ai_sentences"] = [{"text": s["text"][:220], "p_ai": s["p_ai"]} for s in sorted(sents, key=lambda s: -s["p_ai"])[:5] if s["p_ai"] >= 0.25]
        out["p_ai_mean"] = round(sum(p) / len(p), 3)
    return out


def similarity_matrix(texts: list[str], n: int = 5) -> list[list[float]]:
    """Pairwise text overlap in [0,1]: shared word 5-grams over the shorter text (containment), so a paraphrased-in-part copy still scores high."""
    sh = [shingles(t, n) for t in texts]
    m = [[1.0] * len(texts) for _ in texts]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            den = min(len(sh[i]), len(sh[j]))
            v = len(sh[i] & sh[j]) / den if den else 0.0
            m[i][j] = m[j][i] = round(v, 3)
    return m
