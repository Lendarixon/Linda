# -*- coding: utf-8 -*-
"""Text structure profile and "structural rarity" (idea after SlopShape, arXiv 2609.15369: human texts sit in rare regions of structural space, LLM texts in dense ones).

Not used in the verdict: it explains what the text looks like. FEATURES are language-neutral counts (paragraphs, sentence rhythm, lists, openers, stock transitions,
punctuation habits). A rarity percentile like the paper's (distance to the 25 nearest neighbours) was tried on our dev sets and did NOT separate human from AI (Cohen d about 0),
so the view uses a small logistic "structure score" instead; reference built by tools/build_structure_ref.py from dev sets only. Everything is computed locally."""
from __future__ import annotations

import math
from collections import Counter
import re
from pathlib import Path

import numpy as np

from . import config

_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
_SENT = re.compile(r"(?<=[.!?…])[\"')»”]*\s+(?=[\"'«“—–-]*[A-ZА-ЯЁĄĆĘŁŃÓŚŹŻ0-9])")
_LIST = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s+", re.M)
_HEAD = re.compile(r"^\s*(?:#{1,6}\s+.+|[^\n.!?:;]{2,70})$", re.M)
_TRIAD = re.compile(r"\b[^\W\d_]+, [^\W\d_]+,? (?:and|or|и|или|oraz|i|lub) [^\W\d_]+", re.I)
_CONTRAST = re.compile(r"\bnot (?:only |just |merely )?[^.;]{2,60}?, but\b|\bnot (?:only|just) \b|\bне (?:только|просто) [^.;]{2,60}?, (?:но|а)\b|\bnie (?:tylko|jedynie) [^.;]{2,60}?, (?:ale|lecz)\b", re.I)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
_FIRST = re.compile(r"\b(?:i|me|my|mine|we|our|us|я|мне|мой|моя|мое|мы|наш|ja|mnie|mój|moja|my|nasz)\b", re.I)
_SECOND = re.compile(r"\b(?:you|your|вы|ваш|вам|ты|твой|ty|ci|wy|wasz|pan|pani)\b", re.I)
_OPENERS = ("however", "moreover", "furthermore", "additionally", "in conclusion", "overall", "in summary", "ultimately", "importantly", "notably",
            "однако", "кроме того", "более того", "таким образом", "в заключение", "в целом", "важно", "наконец",
            "jednak", "ponadto", "co więcej", "podsumowując", "w rezultacie", "warto", "ostatecznie")
_CONCL = ("in conclusion", "to sum up", "in summary", "overall,", "ultimately", "в заключение", "таким образом", "подводя итог", "в итоге", "podsumowując", "podsumowanie", "w konkluzji")

FEATURES = [
    ("par_per_100w", "paragraphs per 100 words"), ("par_len_mean", "mean paragraph length (log words)"), ("par_len_cv", "paragraph length variation"),
    ("first_par_share", "share of the first paragraph"), ("last_par_share", "share of the last paragraph"), ("sent_per_par", "sentences per paragraph"),
    ("sent_len_mean", "mean sentence length"), ("sent_len_cv", "sentence length variation"), ("short_sent", "short sentences (<=6 words)"), ("long_sent", "long sentences (>=30 words)"),
    ("heading_lines", "heading-like lines"), ("list_items", "list items"), ("bold_marks", "bold / markdown marks per 1000 words"),
    ("colon", "colons per 100 words"), ("dash", "dashes per 100 words"), ("semicolon", "semicolons per 100 words"), ("paren", "parentheses per 100 words"),
    ("question", "questions"), ("exclaim", "exclamations"), ("quotes", "quotation marks per 100 words"), ("digits", "numbers per 100 words"),
    ("first_person", "first person"), ("second_person", "second person (you)"), ("opener_div", "variety of sentence openers"), ("opener_rep", "most repeated opener"),
    ("stock_opener", "stock transition openers"), ("concl_last", "conclusion cue in the last paragraph"), ("comma_per_sent", "commas per sentence"),
    ("triads", "lists of three per 100 sentences"), ("contrast", "'not only… but' patterns per 1000 words"), ("mattr", "lexical diversity"), ("word_len", "mean word length"),
    ("caps", "capitalised words"), ("ellipsis", "ellipses per 1000 words"), ("emoji", "emoji per 1000 words"), ("par_end_q", "paragraphs ending with a question"),
]
KEYS = [k for k, _ in FEATURES]
NAMES = dict(FEATURES)


def _mattr(ws: list[str], window: int = 50) -> float:
    if len(ws) < window:
        return len(set(ws)) / len(ws) if ws else 0.0
    step = max(1, (len(ws) - window) // 40)
    v = [len(set(ws[i:i + window])) / window for i in range(0, len(ws) - window + 1, step)]
    return sum(v) / len(v)


def _cv(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) / m if m else 0.0


def features(text: str) -> dict[str, float]:
    text = text.strip()
    pars = [p for p in re.split(r"\n\s*\n", text) if p.strip()] or [text]
    if len(pars) == 1 and text.count("\n") >= 3:  # one line per paragraph
        pars = [p for p in text.split("\n") if p.strip()]
    sents = [s.strip() for s in _SENT.split(text) if s.strip()] or [text]
    ws = [w.lower() for w in _WORD.findall(text)]
    nw = max(1, len(text.split()))
    pl = [len(p.split()) for p in pars]
    sl = [len(s.split()) for s in sents]
    lines = [l for l in text.split("\n") if l.strip()]
    firsts = [(_WORD.findall(s) or [""])[0].lower() for s in sents]
    low = text.lower()
    sent_low = [s.lower() for s in sents]
    per100 = 100.0 / nw
    last = pars[-1].lower()
    f = {
        "par_per_100w": len(pars) * per100, "par_len_mean": math.log1p(sum(pl) / len(pl)), "par_len_cv": _cv(pl),
        "first_par_share": pl[0] / nw, "last_par_share": pl[-1] / nw, "sent_per_par": len(sents) / len(pars),
        "sent_len_mean": sum(sl) / len(sl), "sent_len_cv": _cv(sl), "short_sent": sum(1 for x in sl if x <= 6) / len(sl), "long_sent": sum(1 for x in sl if x >= 30) / len(sl),
        "heading_lines": (len(_HEAD.findall(text)) - 0) / max(1, len(lines)) if len(lines) > 1 else 0.0,
        "list_items": len(_LIST.findall(text)) / max(1, len(lines)),
        "bold_marks": (text.count("**") + text.count("__")) * 1000.0 / nw,
        "colon": text.count(":") * per100, "dash": (text.count("—") + text.count("–") + text.count(" - ")) * per100, "semicolon": text.count(";") * per100,
        "paren": text.count("(") * per100, "question": sum(1 for s in sents if s.endswith("?")) / len(sents), "exclaim": sum(1 for s in sents if s.endswith("!")) / len(sents),
        "quotes": (text.count('"') + text.count("«") + text.count("“")) * per100, "digits": len(re.findall(r"\d+", text)) * per100,
        "first_person": len(_FIRST.findall(text)) * per100, "second_person": len(_SECOND.findall(text)) * per100,
        "opener_div": len(set(firsts)) / len(firsts), "opener_rep": max(Counter(firsts).values(), default=0) / len(firsts),
        "stock_opener": sum(1 for s in sent_low if s.startswith(_OPENERS)) / len(sents), "concl_last": 1.0 if any(c in last for c in _CONCL) else 0.0,
        "comma_per_sent": text.count(",") / len(sents), "triads": len(_TRIAD.findall(text)) * 100.0 / len(sents),
        "contrast": len(_CONTRAST.findall(text)) * 1000.0 / nw, "mattr": _mattr(ws), "word_len": sum(map(len, ws)) / len(ws) if ws else 0.0,
        "caps": sum(1 for w in text.split() if w[:1].isupper()) / nw, "ellipsis": (text.count("…") + text.count("...")) * 1000.0 / nw,
        "emoji": len(_EMOJI.findall(text)) * 1000.0 / nw, "par_end_q": sum(1 for p in pars if p.rstrip().endswith("?")) / len(pars),
    }
    return {k: float(f[k]) for k in KEYS}


def vector(text: str) -> np.ndarray:
    f = features(text)
    return np.array([f[k] for k in KEYS], dtype=np.float64)


REF_PATH = Path(__file__).resolve().parent / "data" / "structure_ref.npz"
_REF: dict | None = None


def reference() -> dict | None:
    """Bundled reference (None if the file is missing: the profile still works, only the medians and the violins are not shown)."""
    global _REF
    if _REF is None:
        if not REF_PATH.exists():
            return None
        z = np.load(REF_PATH, allow_pickle=False)
        _REF = {k: z[k] for k in z.files}
    return _REF


def layout(text: str, sentences: list[dict] | None = None) -> list[dict]:
    """Paragraph blocks for the structure map: words per paragraph and, when sentence labels are known, one tick per sentence (label + p_ai)."""
    pars = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S[\s\S]*?(?=\n\s*\n|\Z)", text)]
    if len(pars) == 1 and text.count("\n") >= 3:
        pars = [(m.start(), m.end(), m.group()) for m in re.finditer(r"[^\n]+", text) if m.group().strip()]
    out = []
    ordered = list(enumerate(sentences or []))
    unordered = any(ordered[i][1].get("start", -1) > ordered[i + 1][1].get("start", -1) for i in range(len(ordered) - 1))
    if unordered:
        ordered.sort(key=lambda item: item[1].get("start", -1))
    first = 0
    for a, b, t in pars:
        row = {"words": len(t.split()), "kind": "list" if _LIST.match(t) else ("heading" if len(t.split()) <= 12 and not t.rstrip().endswith((".", "!", "?", "…")) else "text")}
        if sentences:
            while first < len(ordered) and ordered[first][1].get("start", -1) < a:
                first += 1
            end = first
            while end < len(ordered) and ordered[end][1].get("start", -1) < b:
                end += 1
            group = ordered[first:end]
            if unordered:
                group.sort(key=lambda item: item[0])  # preserve input order within each paragraph
            row["sentences"] = [{"label": s["label"], "p_ai": s["p_ai"], "words": len(s["text"].split())} for _, s in group]
            first = end
        out.append(row)
    return out


def profile(text: str, sentences: list[dict] | None = None) -> dict:
    """Structure view: paragraph/sentence map, feature values next to the human and AI medians of the reference, and the sentence-level AI probability of human and AI
    reference sentences for the violin comparison. Descriptive only: it does not enter the verdict (see the module docstring for why there is no structure score)."""
    v = vector(text)
    out = {"features": [{"key": k, "name": NAMES[k], "value": round(float(x), 3)} for k, x in zip(KEYS, v)], "layout": layout(text, sentences), "reference": None}
    ref = reference()
    if ref is None or len(v) != ref["std"].shape[0]:
        return out
    for i, row in enumerate(out["features"]):
        lo, hi = float(ref["human_q25"][i]), float(ref["human_q75"][i])
        row.update(human_median=round(float(ref["human_med"][i]), 3), ai_median=round(float(ref["ai_med"][i]), 3), human_range=[round(lo, 3), round(hi, 3)],
                   ai_range=[round(float(ref["ai_q25"][i]), 3), round(float(ref["ai_q75"][i]), 3)],
                   position="above_human" if v[i] > hi else ("below_human" if v[i] < lo else "in_human_range"))
    out["reference"] = {"human_hist": ref["hist_human"].tolist(), "ai_hist": ref["hist_ai"].tolist(), "n_texts": int(ref["n_texts"]), "n_sentences": [int(x) for x in ref["n_sent"]]}
    return out
