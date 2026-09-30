# -*- coding: utf-8 -*-
"""Голоса Linda-Pro: классификатор-трансформер (окна по токенам) и стилометрия (LightGBM + n-граммы, CPU).

Самодостаточно: ничего из исходного репозитория проекта не нужно. Стилометрия и очистка текста — во вложенной копии `_vendor/aidetector`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np


def clean_text(text: str) -> str:
    """Та же очистка от атак (гомоглифы, невидимые символы и т.п.), что использовалась при калибровке."""
    from ._vendor.aidetector.canonical import prepare_for_voter

    return prepare_for_voter("compare", text, "en")


class FastSeqCls:
    """Классификатор-трансформер (DeBERTa). Длинный текст режется на окна `max_len` токенов с полным покрытием, оценка текста —
    средняя логит-разность «ИИ минус человек» по окнам. Тело модели в bf16 (на GPU), голова в fp32."""

    def __init__(self, model_dir: str | Path, batch: int = 32, device: str | None = None):
        self.model_dir = Path(model_dir)
        args = self.model_dir / "train_args.json"
        self.max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
        self.batch = batch
        self.device_pref = device
        self.model = None

    def _load(self) -> None:
        import inspect

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.device = self.device_pref or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = AutoTokenizer.from_pretrained(str(self.model_dir))
        self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir)).to(self.device).eval()
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
        if self.device != "cuda":
            return m(**enc).logits.float()
        base = getattr(m, m.base_model_prefix, None)
        if base is not None and hasattr(m, "pooler") and hasattr(m, "classifier"):
            with torch.autocast("cuda", dtype=torch.bfloat16):
                h = base(**enc)[0]
            return m.classifier(m.pooler(h.float())).float()
        with torch.autocast("cuda", dtype=torch.bfloat16):
            return m(**enc).logits.float()

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
    """Стилометрия (~250 признаков + n-граммы -> LightGBM), только CPU, миллисекунды на текст."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = str(model_dir)

    def margins(self, texts: list[str]) -> list[float]:
        from ._vendor.aidetector.stylometry import load_model

        m = load_model("en", self.model_dir)
        if m is None:
            raise FileNotFoundError(f"stylometry model files not found in {self.model_dir}")
        return m.margins(texts).tolist()

    def close(self) -> None:
        return None
