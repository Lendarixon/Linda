# -*- coding: utf-8 -*-
"""Linda-Pro voices: transformer classifier (token windows) and stylometry (LightGBM + n-grams, CPU).

Self-contained: nothing from the original project repository is needed. Stylometry and text cleaning are in the nested copy `_vendor/aidetector`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import unicodedata

import numpy as np


def clean_text(text: str, lang: str | None = None) -> str:
    """The same attack cleaning (homoglyphs, invisible characters, etc.) that was used during calibration.

    lang selects the document script (ru -> CYRILLIC, en/pl -> LATIN, None -> auto).
    Text is NFC-normalized first so composed/decomposed diacritics (PL from Word/macOS) behave the same.
    """
    from ._vendor.aidetector.canonical import prepare_for_voter

    if text:
        try:
            text = unicodedata.normalize("NFC", text)
        except Exception:  # noqa: BLE001 — normalization must never break scoring
            pass
    return prepare_for_voter("compare", text, lang)


CANCEL = None  # callable -> bool: приложение ставит на время проверки; True = прервать между пакетами


class Cancelled(Exception):
    """Проверка прервана (пользователь вставил новый текст или нажал отмену)."""


def check_cancel() -> None:
    if CANCEL is not None and CANCEL():
        raise Cancelled()


def load_token_head(model_dir):
    """Load the small calibrated head without importing torch."""
    with np.load(Path(model_dir) / "tok_head.npz", allow_pickle=False) as f:
        head = {k: f[k].astype(np.float32 if k in ("w", "b") else np.float64) for k in ("w", "b", "center", "scale")}
        head["conv"] = f["conv"].astype(np.float32) if "conv" in f else np.ones(1, np.float32)
    if (head["w"].ndim != 1 or head["conv"].ndim != 1 or not len(head["conv"])
            or len(head["conv"]) % 2 != 1 or any(not np.isfinite(v).all() for v in head.values())
            or any(head[k].size != 1 for k in ("b", "center", "scale")) or float(head["scale"]) <= 0):
        raise ValueError("Invalid calibrated token head")
    return head


def apply_token_head(hidden, head):
    z = hidden.astype(np.float32) @ head["w"] + float(head["b"])
    radius = len(head["conv"]) // 2
    scores = np.correlate(np.pad(z, (radius, radius)), head["conv"], mode="valid")
    if not np.isfinite(scores).all():
        raise ValueError("Nonfinite token scores")
    return scores


def pro_token_scores(voter, text, hidden_for_window, hidden_for_windows=None):
    """Whole-text coverage, 25% overlap; correlate real tokens per window.

    `hidden_for_window(seq)` scores one window. When `hidden_for_windows(seqs)` is
    given, all windows are planned first and inferred `voter.batch` at a time (one
    forward per batch instead of one per window); scores are then scattered back by
    the same offsets, so coverage and averaging stay identical.
    """
    head = load_token_head(voter.model_dir)
    enc = voter.tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offsets = enc["input_ids"], enc["offset_mapping"]
    n = voter.max_len - 2
    if n < 1:
        raise ValueError("max_len must exceed 2")
    total, count = np.zeros(len(ids)), np.zeros(len(ids))
    starts, real_idx = [], []
    start = 0
    while start < len(ids):
        part = ids[start:start + n]
        starts.append(start)
        real_idx.append([i for i in range(len(part)) if offsets[start + i][1] > offsets[start + i][0]])
        if start + n >= len(ids):
            break
        start += max(1, n * 3 // 4)

    def accumulate(start, real, hidden):
        if not real:
            return
        scores = apply_token_head(hidden[np.array(real) + 1], head)
        idx = start + np.array(real)
        total[idx] += scores
        count[idx] += 1

    if hidden_for_windows is None:
        for start, real in zip(starts, real_idx):
            check_cancel()
            accumulate(start, real, hidden_for_window([voter.tok.cls_token_id, *ids[start:start + n], voter.tok.sep_token_id]))
    else:
        batch = max(1, int(getattr(voter, "batch", 1) or 1))
        # Similar lengths in one batch: the last window is short, so keep it out
        # of a batch of full windows rather than padding it up to max_len.
        order = sorted(range(len(starts)), key=lambda j: -(len(ids[starts[j]:starts[j] + n])))
        for b in range(0, len(order), batch):
            check_cancel()
            chunk = order[b:b + batch]
            seqs = [[voter.tok.cls_token_id, *ids[starts[j]:starts[j] + n], voter.tok.sep_token_id] for j in chunk]
            hiddens = hidden_for_windows(seqs)
            for j, hidden in zip(chunk, hiddens):
                accumulate(starts[j], real_idx[j], hidden)
    return [(a, b, float(total[i] / count[i])) for i, (a, b) in enumerate(offsets) if b > a and count[i]]


class _BareTokenizer:
    """HF-compatible facade over a bare `tokenizers.Tokenizer`.

    AutoTokenizer imports every transformers model module and its Python wrapper adds
    a BatchEncoding around each call; the Rust tokenizer produces the same ids and
    offsets on its own (tested on EN/PL/RU). Loading it never requires transformers,
    which the packaged app may not ship for tokenization-only work.
    """

    def __init__(self, tk):
        self._tk = tk
        self._tk.no_padding()  # tokenizer.json may carry training-time padding/truncation
        self._tk.no_truncation()
        self.cls_token_id = tk.token_to_id("[CLS]")
        self.sep_token_id = tk.token_to_id("[SEP]")
        self.pad_token_id = tk.token_to_id("[PAD]")
        self.unk_token_id = tk.token_to_id("[UNK]")
        self.mask_token_id = tk.token_to_id("[MASK]")

    def _one(self, text, add_special_tokens):
        return self._tk.encode(text, add_special_tokens=bool(add_special_tokens))

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False, **_kwargs):
        if isinstance(text, str):
            e = self._one(text, add_special_tokens)
            out = {"input_ids": list(e.ids)}
            if return_offsets_mapping:
                out["offset_mapping"] = [tuple(o) for o in e.offsets]
            return out
        encs = [self._one(t, add_special_tokens) for t in text]
        out = {"input_ids": [list(e.ids) for e in encs]}
        if return_offsets_mapping:
            out["offset_mapping"] = [[tuple(o) for o in e.offsets] for e in encs]
        return out

    def encode(self, text, add_special_tokens=False):
        return self._one(text, add_special_tokens)

    def pad(self, enc, return_tensors=None, pad_to_multiple_of=None, **_kwargs):
        ids = enc["input_ids"]
        if ids and not isinstance(ids[0], (list, tuple)):
            ids = [ids]
        width = max((len(x) for x in ids), default=0)
        if pad_to_multiple_of:
            width += -width % int(pad_to_multiple_of)
        arr = np.full((len(ids), width), self.pad_token_id, dtype=np.int64)
        mask = np.zeros((len(ids), width), dtype=np.int64)
        for row, x in enumerate(ids):
            arr[row, :len(x)] = x
            mask[row, :len(x)] = 1
        if return_tensors == "pt":
            import torch

            return {"input_ids": torch.from_numpy(arr), "attention_mask": torch.from_numpy(mask)}
        return {"input_ids": arr.tolist(), "attention_mask": mask.tolist()}


def load_bare_tokenizer(model_dir):
    """`tokenizers.Tokenizer.from_file(model_dir/tokenizer.json)`, or None when unavailable."""
    try:
        from tokenizers import Tokenizer

        path = Path(model_dir) / "tokenizer.json"
        if not path.is_file():
            return None
        return _BareTokenizer(Tokenizer.from_file(str(path)))
    except Exception:  # noqa: BLE001 — packaged app without the tokenizers lib: fall back to AutoTokenizer
        return None



class FastSeqCls:
    """Transformer classifier (DeBERTa). Long text is sliced into windows of `max_len` tokens with full coverage, text score is
    the average logit difference "AI minus human" across windows. Model body in bf16 (on GPU), head in fp32."""

    def __init__(self, model_dir: str | Path, batch: int = 32, device: str | None = None, force_fp32: bool = False):
        self.model_dir = Path(model_dir)
        args = self.model_dir / "train_args.json"
        self.max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
        self.batch = batch
        self.device_pref = device
        self.force_fp32 = force_fp32
        self.model = None

    def _load(self) -> None:
        import inspect

        import torch
        from transformers import AutoModelForSequenceClassification

        self.torch = torch
        self.device = self.device_pref or ("cuda" if torch.cuda.is_available() else "cpu")
        # Bare Rust tokenizer first: identical ids/offsets to AutoTokenizer (see
        # tests/test_bare_tokenizer.py) without importing every model module.
        self.tok = load_bare_tokenizer(self.model_dir)
        if self.tok is None:
            from transformers import AutoTokenizer

            self.tok = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir)).to(self.device).eval()
        if self.device == "cpu" or self.force_fp32:  # downloads may be fp16; calibrated routes run FP32
            self.model = self.model.float()
        self.args = set(inspect.signature(self.model.forward).parameters)

    def close(self) -> None:
        self.model = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:  # noqa: BLE001
            pass

    def _logits(self, enc):
        torch, m = self.torch, self.model
        if self.device != "cuda" or self.force_fp32:
            return m(**enc).logits.float()
        base = getattr(m, m.base_model_prefix, None)
        if base is not None and hasattr(m, "pooler") and hasattr(m, "classifier"):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                h = base(**enc)[0]
            return m.classifier(m.pooler(h.float())).float()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            return m(**enc).logits.float()

    @property
    def has_token_scores(self):
        return (self.model_dir / "tok_head.npz").is_file()

    def token_scores(self, text):
        if not self.has_token_scores:
            raise ValueError("Missing tok_head.npz")
        if self.model is None:
            self._load()

        base = getattr(self.model, self.model.base_model_prefix)

        def hidden(seq):
            enc = self.tok.pad({"input_ids": [seq]}, return_tensors="pt", pad_to_multiple_of=32)
            enc = {k: v.to(self.device) for k, v in enc.items() if k in self.args}
            with self.torch.no_grad():
                return base(**enc).last_hidden_state[0].float().cpu().numpy()

        def hidden_batch(seqs):
            # One forward for the whole batch. DeBERTa v2 positions are relative
            # (position_biased_input=false), so right padding never moves a real
            # token; the mask keeps padding out of attention and pooling.
            enc = self.tok.pad({"input_ids": seqs}, return_tensors="pt", pad_to_multiple_of=32)
            enc = {k: v.to(self.device) for k, v in enc.items() if k in self.args}
            with self.torch.no_grad():
                out = base(**enc).last_hidden_state.float().cpu().numpy()
            return [out[row, :len(seq)] for row, seq in enumerate(seqs)]

        return pro_token_scores(self, text, hidden, hidden_batch)

    def _windows(self, ids: list[int]) -> list[list[int]]:
        n = self.max_len - 2
        if len(ids) <= n:
            return [ids]
        k = math.ceil(len(ids) / n)
        starts = np.linspace(0, len(ids) - n, k).round().astype(int)
        return [ids[s: s + n] for s in starts]

    def margins(self, texts: list[str]) -> list[float]:
        if self.model is None:
            self._load()
        torch, tok = self.torch, self.tok
        all_ids = tok(texts, add_special_tokens=False)["input_ids"]
        wins, owner = [], []
        for i, ids in enumerate(all_ids):
            for w in self._windows(ids) or [[]]:
                wins.append([tok.cls_token_id, *w, tok.sep_token_id])
                owner.append(i)
        order = sorted(range(len(wins)), key=lambda j: len(wins[j]))
        z = np.zeros(len(wins))
        for b in range(0, len(order), self.batch):
            check_cancel()
            idx = order[b: b + self.batch]
            enc = tok.pad({"input_ids": [wins[j] for j in idx]}, return_tensors="pt", pad_to_multiple_of=32)
            enc = {k: v.to(self.device) for k, v in enc.items() if k in self.args}
            with torch.no_grad():
                lg = self._logits(enc)
            m = lg[:, 1] - lg[:, 0] if lg.shape[1] == 2 else lg[:, 0]
            z[idx] = m.cpu().numpy()
        out = np.zeros(len(texts))
        cnt = np.zeros(len(texts))
        np.add.at(out, owner, z)
        np.add.at(cnt, owner, 1)
        return (out / cnt).tolist()


class StyloVoter:
    """Stylometry (~250 features + n-grams -> LightGBM), CPU only, milliseconds per text."""

    def __init__(self, model_dir: str | Path, lang: str = "en"):
        self.model_dir = str(model_dir)
        self.lang = lang

    def margins(self, texts: list[str]) -> list[float]:
        from ._vendor.aidetector.stylometry import load_model

        m = load_model(self.lang, self.model_dir)
        if m is None:
            raise FileNotFoundError(f"stylometry model files not found in {self.model_dir}")
        return m.margins(texts).tolist()

    def close(self) -> None:
        return None


class SpeedOnnx:
    """Linda-Speed voter: small multilingual encoder (ONNX, int8) on the CPU. One 300-word window = one pass over the first `max_len` tokens;
    the score is in the units of the large ensemble's window score (distilled). `model_dir` holds model.onnx (fp32, pruned vocabulary), speed_args.json, encoder/ (tokenizer)
    and, when the vocabulary was pruned, vocab_map.npy (old token id -> new id)."""

    def __init__(self, model_dir: str | Path, threads: int | None = None, batch: int = 12):
        self.model_dir = Path(model_dir)
        self.threads, self.batch, self.sess = threads, batch, None

    def _load(self) -> None:
        import os

        import onnxruntime as ort
        from tokenizers import Tokenizer  # the bare tokenizer: AutoTokenizer would import every transformers model module (missing in the packaged app)

        args = json.loads((self.model_dir / "speed_args.json").read_text(encoding="utf-8"))
        self.max_len = int(args.get("max_len", 256))
        self.max_slices = int(args.get("max_slices", 4))
        self.special_ids = (args.get("bos_id"), args.get("eos_id"), args.get("pad_id"))  # mmBERT students: <s>/</s> are not bos/eos
        self.sliced = bool(args.get("sliced", False))  # students trained on the first max_len tokens only must not be fed the rest
        self.tok = Tokenizer.from_file(str(self.model_dir / "encoder" / "tokenizer.json"))
        self.tok.no_padding()  # tokenizer.json carries the training-time padding/truncation settings; slicing and padding are done in margins()
        self.tok.no_truncation()
        vm = self.model_dir / "vocab_map.npy"
        self.vmap = np.load(vm) if vm.exists() else None
        so = ort.SessionOptions()
        so.intra_op_num_threads = self.threads or max(1, min(4, (os.cpu_count() or 4)))
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(str(self.model_dir / "model.onnx"), so, providers=["CPUExecutionProvider"])

    def margins(self, texts: list[str]) -> list[float]:
        """Every text is cut into token slices of `max_len` that cover ALL its tokens (as the large models do); the score is the mean over the slices."""
        return self._margins(texts)[0]

    def _special(self, cls_id, sep_id, pad_id):
        """speed_args.json bos_id/eos_id/pad_id override the RoBERTa-style <s>/</s>/<pad> lookup (absent = old behaviour)."""
        sb, se, sp = getattr(self, "special_ids", (None, None, None))
        return (cls_id if sb is None else sb), (sep_id if se is None else se), (pad_id if sp is None else sp)

    def margins_with_token_scores(self, texts):
        """Keep the token head from the very same verdict inference calls."""
        return self._margins(texts, keep_tokens=True)

    def _margins(self, texts, keep_tokens=False):
        if self.sess is None:
            self._load()
        keep_tokens = keep_tokens and not self.sliced and self.has_token_scores
        n = self.max_len - 2
        cls_id, sep_id, pad_id = self.tok.token_to_id("<s>"), self.tok.token_to_id("</s>"), self.tok.token_to_id("<pad>")
        cls_id, sep_id, pad_id = self._special(cls_id, sep_id, pad_id)
        seqs, owner = [], []
        encodings = self.tok.encode_batch(texts, add_special_tokens=False)
        known = [[] for _ in texts]
        for i, enc in enumerate(encodings):
            ids = enc.ids
            parts = [ids] if len(ids) <= n else ([ids[s: s + n] for s in np.linspace(0, len(ids) - n, min(self.max_slices, -(-len(ids) // n))).round().astype(int)] if self.sliced else [ids[:n]])
            for part in parts:
                seqs.append([cls_id, *part, sep_id])
                owner.append(i)
        order = sorted(range(len(seqs)), key=lambda j: len(seqs[j]))
        z = np.zeros(len(seqs))
        for b in range(0, len(order), self.batch):
            check_cancel()
            idx = order[b: b + self.batch]
            width = max(len(seqs[j]) for j in idx)
            ids = np.full((len(idx), width), pad_id, dtype=np.int64)
            mask = np.zeros((len(idx), width), dtype=np.int64)
            for r, j in enumerate(idx):
                ids[r, : len(seqs[j])] = seqs[j]
                mask[r, : len(seqs[j])] = 1
            if self.vmap is not None:
                ids = self.vmap[ids].astype(np.int64)
            outputs = self.sess.run(None, {"input_ids": ids, "attention_mask": mask})
            z[idx] = outputs[0][:, 0]
            if keep_tokens:
                names = [o.name for o in self.sess.get_outputs()]
                tok = outputs[names.index("tok")]
                if tok.shape == ids.shape:
                    for row, j in enumerate(idx):
                        enc = encodings[owner[j]]
                        content_scores = tok[row, 1:len(seqs[j]) - 1]
                        # Bad token evidence falls back window by window. The
                        # verdict output and valid sibling rows remain usable;
                        # special/padding positions are never reused.
                        if not np.isfinite(content_scores).all():
                            continue
                        known[owner[j]] = [(a, b, float(score), token_id)
                                          for (a, b), score, token_id in zip(enc.offsets[:n], content_scores, enc.ids[:n])
                                          if b > a]
        out, cnt = np.zeros(len(texts)), np.zeros(len(texts))
        np.add.at(out, owner, z)
        np.add.at(cnt, owner, 1)
        return (out / np.maximum(cnt, 1)).tolist(), known

    def token_scores_reuse(self, text, known):
        """Reuse exact original offsets/IDs; infer only uncovered runs, without overlap.

        Known entries are (start, end, score, token_id). Matching IDs as well as
        offsets avoids reusing tokens whose encoding changed at a window edge.
        """
        from collections import defaultdict, deque

        if self.sess is None:
            self._load()
        if not self.has_token_scores:
            raise ValueError("SpeedOnnx.token_scores requires model output 'tok'")
        n = self.max_len - 2
        if n < 1 or self.batch < 1:
            raise ValueError("max_len must exceed 2 and batch must be positive")
        check_cancel()
        enc = self.tok.encode(text, add_special_tokens=False)
        available = defaultdict(deque)
        for a, b, score, token_id in known:
            if 0 <= a < b <= len(text) and np.isfinite(score):
                available[a, b, token_id].append(float(score))
        scores = np.zeros(len(enc.ids), dtype=np.float64)
        covered = np.zeros(len(enc.ids), dtype=bool)
        for i, ((a, b), token_id) in enumerate(zip(enc.offsets, enc.ids)):
            values = available.get((a, b, token_id))
            if values:
                scores[i], covered[i] = values.popleft(), True
        chunks = []
        start = 0
        while start < len(enc.ids):
            if covered[start]:
                start += 1
                continue
            end = start + 1
            while end < len(enc.ids) and not covered[end]:
                end += 1
            chunks.extend((s, min(s + n, end)) for s in range(start, end, n))
            start = end
        # Like verdict inference, group similar lengths to avoid padding short
        # uncovered runs to the longest chunk in an unrelated batch.
        chunks.sort(key=lambda span: span[1] - span[0])
        cls_id, sep_id, pad_id = (self.tok.token_to_id(t) for t in ("<s>", "</s>", "<pad>"))
        cls_id, sep_id, pad_id = self._special(cls_id, sep_id, pad_id)
        for batch_start in range(0, len(chunks), self.batch):
            check_cancel()
            batch = chunks[batch_start:batch_start + self.batch]
            width = max(b - a + 2 for a, b in batch)
            ids = np.full((len(batch), width), pad_id, dtype=np.int64)
            mask = np.zeros_like(ids)
            for row, (a, b) in enumerate(batch):
                seq = [cls_id, *enc.ids[a:b], sep_id]
                ids[row, :len(seq)], mask[row, :len(seq)] = seq, 1
            if self.vmap is not None:
                ids = self.vmap[ids].astype(np.int64)
            tok = self.sess.run(["tok"], {"input_ids": ids, "attention_mask": mask})[0]
            if tok.shape != ids.shape or not np.isfinite(tok).all():
                raise ValueError("Model output 'tok' must contain finite [batch, seq] scores")
            for row, (a, b) in enumerate(batch):
                scores[a:b] = tok[row, 1:b - a + 1]
        return [(a, b, float(score)) for (a, b), score in zip(enc.offsets, scores)]

    def token_scores(self, text: str) -> list[tuple[int, int, float]]:
        """Score every content token, averaging windows with 25% overlap (50% cost ~1.5x more for no measurable gain).

        Offsets refer to the original text; CLS/SEP and padding are excluded.
        Unlike margins(), this covers the entire text regardless of sliced or
        max_slices. Each token keeps one result, averaged over its windows.
        This requires a Lite model exported with the additional ``tok`` output.
        """
        if self.sess is None:
            self._load()
        if "tok" not in {o.name for o in self.sess.get_outputs()}:
            raise ValueError("SpeedOnnx.token_scores requires model output 'tok'")
        n = self.max_len - 2
        if n < 1 or self.batch < 1:
            raise ValueError("max_len must exceed 2 and batch must be positive")
        check_cancel()
        enc = self.tok.encode(text, add_special_tokens=False)
        if not enc.ids:
            return []
        starts = []
        start = 0
        while True:
            starts.append(start)
            if start + n >= len(enc.ids):
                break
            start += max(1, (n * 3) // 4)
        cls_id = self.tok.token_to_id("<s>")
        sep_id = self.tok.token_to_id("</s>")
        pad_id = self.tok.token_to_id("<pad>")
        total = np.zeros(len(enc.ids), dtype=np.float64)
        count = np.zeros(len(enc.ids), dtype=np.int64)
        for b in range(0, len(starts), self.batch):
            check_cancel()
            chunk_starts = starts[b:b + self.batch]
            parts = [enc.ids[s:s + n] for s in chunk_starts]
            width = max(len(p) + 2 for p in parts)
            ids = np.full((len(parts), width), pad_id, dtype=np.int64)
            mask = np.zeros_like(ids)
            for row, part in enumerate(parts):
                seq = [cls_id, *part, sep_id]
                ids[row, :len(seq)] = seq
                mask[row, :len(seq)] = 1
            if self.vmap is not None:
                ids = self.vmap[ids].astype(np.int64)
            tok = self.sess.run(["tok"], {"input_ids": ids, "attention_mask": mask})[0]
            if tok.shape != ids.shape or not np.isfinite(tok).all():
                raise ValueError("Model output 'tok' must contain finite [batch, seq] scores")
            for row, (s, part) in enumerate(zip(chunk_starts, parts)):
                end = s + len(part)
                total[s:end] += tok[row, 1:len(part) + 1]
                count[s:end] += 1
        scores = total / count
        return [(a, b, float(score)) for (a, b), score in zip(enc.offsets, scores)]

    @property
    def has_token_scores(self):
        if self.sess is None:
            self._load()
        return "tok" in {o.name for o in self.sess.get_outputs()}

    def close(self) -> None:
        self.sess = None


class StyloTVoter:
    """Stylo-T: stylometry (hand features -> LightGBM) trained to reproduce the large models' window scores; CPU, milliseconds per window. One model per language."""

    def __init__(self, model_dir: str | Path, lang: str):
        self.path, self.lang, self.booster = Path(model_dir) / f"{lang}.lgb.txt", lang, None

    def margins(self, texts: list[str]) -> list[float]:
        import lightgbm as lgb

        from ._vendor.aidetector.stylometry import feature_vector

        if self.booster is None:
            self.booster = lgb.Booster(model_str=self.path.read_text(encoding="utf-8"))  # model_str: Booster(model_file=) fails on non-ASCII paths
        X = np.array([feature_vector(t, self.lang) for t in texts], dtype=np.float32)
        return [float(v) for v in self.booster.predict(X)]

    def close(self) -> None:
        self.booster = None
