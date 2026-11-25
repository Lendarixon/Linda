# -*- coding: utf-8 -*-
"""One-pass AI/human span segmenter (mmBERT-small token classifier, ONNX CPU).

The model labels every token with P(AI); sentences are scored from those tokens,
a 2-state Viterbi (switch penalty lambda, minimum segment length) turns the
sentence scores into contiguous segments, and each segment is banded:

    ai        mean p >= 0.8
    human     mean p <= 0.1        (>= 0.9 confidence in "human")
    unsure    otherwise

The DP, the sentence splitter and the bands are the same as the research
reference (`l14_seg_dp.py`); they are copied here so the product does not import
the research tree. Documents longer than the model window are scored in
overlapping token windows and each token keeps the mean of its windows.

Public API
    Segmenter(model_dir, threads).segment(text) -> [{start, end, label, p}]
    Segmenter.available()            # model files present and loadable
    fraction_ai(segments)            # character-weighted share of AI text
"""
from __future__ import annotations

import json
import math
from pathlib import Path

AI_BAND = 0.8
HUMAN_BAND = 0.1
LOG_EPS = 1e-6

# Sentence splitter of the reference implementation (aidetector.text_utils):
# a terminator followed by whitespace and a letter/digit, or a blank line.
import re

_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?…])[\"')»”]*\s+(?=[\"'«“—–-]*[А-ЯЁA-ZĄĆĘŁŃÓŚŹŻ0-9])|\n\s*\n"
)


def split_sentences_with_offsets(text: str) -> list[tuple[int, int, str]]:
    """[(start, end, sentence)] with offsets in the original text."""
    out: list[tuple[int, int, str]] = []
    prev = 0
    for m in _SENTENCE_SPLIT_RE.finditer(text):
        chunk = text[prev: m.start()]
        stripped = chunk.strip()
        if stripped:
            off = prev + chunk.find(stripped)
            out.append((off, off + len(stripped), stripped))
        prev = m.end()
    chunk = text[prev:]
    stripped = chunk.strip()
    if stripped:
        off = prev + chunk.find(stripped)
        out.append((off, off + len(stripped), stripped))
    return out


def word_count(s: str) -> int:
    return max(1, len([w for w in s.split() if any(c.isalnum() for c in w)]))


def sentence_scores(offsets, probs, sents) -> list[float]:
    """Per-sentence AI score = char-length-weighted mean of its token probabilities.

    A token belongs to the sentence when the midpoint of its char span falls
    inside the sentence span; the weight is the token char length (>= 1).
    """
    wsum = [0.0] * len(sents)
    psum = [0.0] * len(sents)
    j = 0
    for (cs, ce), p in zip(offsets, probs):
        if ce <= cs:  # special token
            continue
        mid = 0.5 * (cs + ce)
        while j < len(sents) - 1 and mid >= sents[j][1]:
            j += 1
        if not (sents[j][0] <= mid < sents[j][1]):
            continue
        w = float(max(1, ce - cs))
        wsum[j] += w
        psum[j] += w * float(p)
    return [(psum[k] / wsum[k]) if wsum[k] > 0 else 0.5 for k in range(len(sents))]


def _log(p: float) -> tuple[float, float]:
    """Log-likelihoods of (human, ai); the DP MAXIMISES their sum."""
    p = min(1 - LOG_EPS, max(LOG_EPS, p))
    return math.log(1.0 - p), math.log(p)


def viterbi(sent_p, sent_words, lam: float, min_words: int) -> list[tuple[int, int, int]]:
    """Max-score segmentation with a per-switch penalty.

    score = sum over sentences of log P(state) - lam * (number of switches),
    subject to every segment (except a whole-document one) having >= min_words
    words. Returns [(i, j, state)] covering sentences [i, j).
    """
    n = len(sent_p)
    if n == 0:
        return []
    emit = [_log(p) for p in sent_p]
    pre = [[0.0, 0.0] for _ in range(n + 1)]
    for k in range(n):
        pre[k + 1][0] = pre[k][0] + emit[k][0]
        pre[k + 1][1] = pre[k][1] + emit[k][1]
    pw = [0] * (n + 1)
    for k in range(n):
        pw[k + 1] = pw[k] + sent_words[k]
    NEG = float("-inf")
    dp = [[NEG, NEG] for _ in range(n + 1)]
    back: list[list[tuple[int, int] | None]] = [[None, None] for _ in range(n + 1)]
    dp[0][0] = dp[0][1] = 0.0
    for j in range(1, n + 1):
        for i in range(j - 1, -1, -1):
            w = pw[j] - pw[i]
            if w < min_words and not (i == 0 and j == n):
                continue
            if i > 0 and dp[i][0] == NEG and dp[i][1] == NEG:
                continue
            for nl in (0, 1):
                seg = pre[j][nl] - pre[i][nl]
                best_c, best_l = NEG, 0
                for l in (0, 1):
                    if dp[i][l] == NEG:
                        continue
                    c = dp[i][l] - (0.0 if (nl == l or i == 0) else lam)
                    if c > best_c:
                        best_c, best_l = c, l
                if best_c == NEG:
                    continue
                c = best_c + seg
                if c > dp[j][nl]:
                    dp[j][nl] = c
                    back[j][nl] = (i, best_l)
    best_l = 0 if dp[n][0] >= dp[n][1] else 1
    if dp[n][best_l] == NEG:  # infeasible (cannot happen: whole doc is allowed)
        return [(0, n, 1 if sum(sent_p) / n >= 0.5 else 0)]
    segs, j, l = [], n, best_l
    while j > 0:
        b = back[j][l]
        if b is None:
            return [(0, n, 1 if sum(sent_p) / n >= 0.5 else 0)]
        i, pl = b
        segs.append((i, j, l))
        j, l = i, pl
    return list(reversed(segs))


def band(mean_p: float, ai_band: float = AI_BAND, human_band: float = HUMAN_BAND) -> str:
    if mean_p >= ai_band:
        return "ai"
    if mean_p <= human_band:
        return "human"
    return "unsure"


def _weighted_mean(values, weights) -> float:
    tot = sum(weights)
    if not values or tot <= 0:
        return 0.5
    return float(sum(v * w for v, w in zip(values, weights)) / tot)


def segments_from_scores(sents, p_sent, lam: float, min_words: int,
                         ai_band: float = AI_BAND, human_band: float = HUMAN_BAND) -> list[dict]:
    """DP over sentence scores -> [{start, end, label, p, state, words}]."""
    words = [word_count(s[2]) for s in sents]
    pieces = viterbi(p_sent, words, lam, min_words)
    # The DP may cut a run of one state into equal-score pieces (a switch costs nothing
    # there); join them so the markup shows one span per stretch. Labels are unaffected.
    merged: list[tuple[int, int, int]] = []
    for i, j, st in pieces:
        if merged and merged[-1][2] == st and merged[-1][1] == i:
            merged[-1] = (merged[-1][0], j, st)
        else:
            merged.append((i, j, st))
    out = []
    for i, j, st in merged:
        ws = [max(1, sents[k][1] - sents[k][0]) for k in range(i, j)]
        mean_p = _weighted_mean(p_sent[i:j], ws)
        out.append({
            "start": sents[i][0],
            "end": sents[j - 1][1],
            "state": "ai" if st == 1 else "human",
            "label": band(mean_p, ai_band, human_band),
            "p": round(mean_p, 4),
            "words": int(sum(words[i:j])),
        })
    return out


def fraction_ai(segments) -> float:
    """Character-weighted share of AI text."""
    ai = tot = 0
    for s in segments:
        n = max(0, int(s["end"]) - int(s["start"]))
        tot += n
        if s.get("state") == "ai":
            ai += n
    return ai / tot if tot else 0.0


class Segmenter:
    """Lazy ONNX CPU segmenter. `segment()` is the only entry point the app needs."""

    WINDOW_OVERLAP = 0.25

    def __init__(self, model_dir: str | Path, threads: int = 4):
        self.model_dir = Path(model_dir)
        self.threads = max(1, int(threads or 4))
        self.sess = None
        self.tok = None
        self.max_len = 2048
        self.lam, self.min_words = 1.0, 6
        self.ai_band, self.human_band = AI_BAND, HUMAN_BAND
        self.labels = ("human", "ai")
        self._ids = (2, 1, 0)  # cls, sep, pad

    # ------------------------------------------------------------------ load
    def exists(self) -> bool:
        """Are the model files on disk (no inference attempted)?"""
        try:
            return ((self.model_dir / "onnx" / "model.onnx").is_file()
                    and (self.model_dir / "tokenizer.json").is_file())
        except OSError:
            return False

    def _load(self) -> None:
        import onnxruntime as ort
        from tokenizers import Tokenizer  # bare tokenizer: AutoTokenizer pulls every transformers model module

        args = {}
        p = self.model_dir / "seg_args.json"
        if p.is_file():
            args = json.loads(p.read_text(encoding="utf-8"))
        self.max_len = int(args.get("max_len", self.max_len) or self.max_len)
        self.labels = tuple(args.get("labels") or self.labels)
        bands = args.get("label_bands") or {}
        self.ai_band = float(bands.get("ai", AI_BAND))
        self.human_band = float(bands.get("human", HUMAN_BAND))
        self.WINDOW_OVERLAP = float(args.get("window_overlap", self.WINDOW_OVERLAP))
        self._ids = (int(args.get("cls_id", 2)), int(args.get("sep_id", 1)), int(args.get("pad_id", 0)))
        dpf = self.model_dir / "dp.json"
        if dpf.is_file():
            cfg = json.loads(dpf.read_text(encoding="utf-8"))
            self.lam = float(cfg.get("lambda", 1.0))
            self.min_words = int(cfg.get("min_words", 6))
            self.ai_band = float(cfg.get("ai_band", self.ai_band))
            self.human_band = float(cfg.get("human_band", self.human_band))
        tokf = self.model_dir / "tokenizer.json"
        if not tokf.is_file():
            tokf = self.model_dir / "onnx" / "tokenizer.json"
        self.tok = Tokenizer.from_file(str(tokf))
        self.tok.no_padding()
        self.tok.no_truncation()
        so = ort.SessionOptions()
        so.intra_op_num_threads = self.threads
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        # CPU only: the app may hold the GPU for the voters, and the segmenter is fast on 4 threads.
        self.sess = ort.InferenceSession(str(self.model_dir / "onnx" / "model.onnx"), so,
                                        providers=["CPUExecutionProvider"])

    def _ensure(self) -> None:
        if self.sess is None:
            if not self.exists():
                raise FileNotFoundError("segmenter model is not installed: %s" % self.model_dir)
            self._load()

    # ------------------------------------------------------------ inference
    def _windows(self, n_tokens: int) -> list[tuple[int, int]]:
        n = max(1, self.max_len - 2)
        if n_tokens <= n:
            return [(0, n_tokens)]
        step = max(1, int(round(n * (1.0 - self.WINDOW_OVERLAP))))
        starts = list(range(0, max(1, n_tokens - n + 1), step))
        if starts[-1] + n < n_tokens:
            starts.append(n_tokens - n)
        return [(s, min(n_tokens, s + n)) for s in starts]

    def token_probs(self, text: str):
        """(offsets, probabilities) for every content token, averaged over windows."""
        import numpy as np

        self._ensure()
        enc = self.tok.encode(text, add_special_tokens=False)
        ids = list(enc.ids)
        offs = list(enc.offsets)
        if not ids:
            return [], []
        cls_id, sep_id, pad_id = self._ids
        total = np.zeros(len(ids), dtype=np.float64)
        count = np.zeros(len(ids), dtype=np.float64)
        n = max(1, self.max_len - 2)
        for a, b in self._windows(len(ids)):
            body = ids[a:b]
            seq = [cls_id, *body, sep_id]
            width = len(seq)
            arr = np.full((1, width), pad_id, dtype=np.int64)
            arr[0] = seq
            mask = np.zeros((1, width), dtype=np.int64)
            mask[0, :width] = 1
            probs = self.sess.run(["ai_prob"], {"input_ids": arr, "attention_mask": mask})[0]
            probs = np.asarray(probs, dtype=np.float64).reshape(-1)
            if probs.size < 1 + len(body):
                raise ValueError("segmenter output shorter than its input")
            vals = probs[1: 1 + len(body)]
            total[a:b] += vals
            count[a:b] += 1.0
        count[count == 0] = 1.0
        return offs, (total / count).tolist()

    # ------------------------------------------------------------------ api
    def segment(self, text: str, sents=None) -> list[dict]:
        """Segments [{start, end, label in ('ai','human','unsure'), p}] covering the text.

        `sents` may carry the caller's own [(start, end, sentence)] spans so the
        app's sentence rows and the DP boundaries line up exactly.
        """
        if not text or not text.strip():
            return []
        self._ensure()
        sents = list(sents) if sents else split_sentences_with_offsets(text)
        if not sents:
            return []
        offs, probs = self.token_probs(text)
        p_sent = sentence_scores(offs, probs, sents)
        return segments_from_scores(sents, p_sent, self.lam, self.min_words,
                                    self.ai_band, self.human_band)

    def scores(self, text: str, sents=None) -> tuple[list, list[float]]:
        """Sentence spans and their AI scores in one inference pass."""
        sents = list(sents) if sents else split_sentences_with_offsets(text)
        if not sents:
            return [], []
        offs, probs = self.token_probs(text)
        return sents, sentence_scores(offs, probs, sents)

    def run(self, text: str, sents=None) -> dict:
        """Segments plus the character-weighted AI share and per-sentence scores."""
        if not text or not text.strip():
            return {"segments": [], "fraction_ai": 0.0, "p_sent": [], "sents": []}
        sents, p_sent = self.scores(text, sents)
        segs = segments_from_scores(sents, p_sent, self.lam, self.min_words,
                                    self.ai_band, self.human_band) if sents else []
        return {"segments": segs, "fraction_ai": round(fraction_ai(segs), 4),
                "p_sent": p_sent, "sents": sents}
