# -*- coding: utf-8 -*-
"""Linda-Pro 1.0 — детектор ИИ-текста (английский), локальный, без облака и API.

Три голоса: стилометрия (stylo7e, CPU), Linda-Essay v3 и Linda-Multi v2 (трансформеры). Текст режется на окна ~300 слов (до 12);
стилометрия читает весь текст, Essay и Multi — каждое окно, агрегат по окнам — top25 (среднее верхней четверти окон).

Вердикт:
  mode='sensitive' (по умолчанию): ai — Essay ИЛИ ансамбль (z-среднее трёх голосов) выше порога 0,5% ложных;
                                   uncertain — выше порога 5%; иначе human.
  mode='precise' (школы, вузы; минимум ложных обвинений): ai — Essay выше порога 1% И стилометрия выше порога 5%;
                                   uncertain — один сильный сигнал; иначе human. На эссе современных моделей ловит заметно меньше.
Доля ИИ (`ai_share`) — доля слов в окнах Essay выше оконного порога 1% (грубая оценка смешанного авторства, разрешение ~300 слов).
Пороги — в calibration/*.json (по людям: эссе, книги, arXiv, веб, новости, отзывы, ESL; см. docs). Не единственное основание для решений о нечестности.
"""
from __future__ import annotations

import json
from pathlib import Path

from .voters import FastSeqCls, StyloVoter, clean_text

PKG_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CALIBRATION = PKG_ROOT / "calibration" / "calibration_windowed_v5.json"
DEFAULT_MODELS = PKG_ROOT / "models"
MODEL_SUBDIRS = {"stylo7c": "stylo7e", "linda_essay": "linda_essay_v3", "linda_multi_v2": "linda_multi_v2"}  # ключи калибровки -> папки
WINDOW_WORDS, MAX_WINDOWS = 300, 12


def split_windows(text: str, words: int = WINDOW_WORDS, maxw: int = MAX_WINDOWS) -> list[tuple[str, int, int]]:
    """Окна ~`words` слов (до `maxw`): [(текст окна, первое слово, слово после последнего)]."""
    w = text.split()
    if len(w) <= words * 1.3:
        return [(text, 0, len(w))]
    n = min(maxw, max(1, round(len(w) / words)))
    step = len(w) / n
    return [(" ".join(w[int(i * step): int((i + 1) * step)]), int(i * step), int((i + 1) * step)) for i in range(n)]


def top25(values: list[float]) -> float:
    v = sorted(float(x) for x in values)
    k = max(1, -(-len(v) // 4))
    return sum(v[-k:]) / k


def verdict(essay: float, ens_z: float, stylo: float, rules: dict, mode: str = "sensitive") -> str:
    e, n = rules["essay"], rules["ensemble"]
    if mode == "precise" and "stylo" in rules:
        if essay > e["thr_1"] and stylo > rules["stylo"]["thr_5"]:
            return "ai"
        if essay > e["thr_1"] or ens_z > n["thr_1"]:
            return "uncertain"
        return "human"
    if essay > e["thr_05"] or ens_z > n["thr_05"]:
        return "ai"
    if essay > e["thr_5"] or ens_z > n["thr_5"]:
        return "uncertain"
    return "human"


class LindaPro:
    def __init__(self, calibration: str | Path | None = None, models_dir: str | Path | None = None, mode: str = "sensitive",
                 device: str | None = None, batch_size: int = 32, voter_factory=None):
        if mode not in ("sensitive", "precise"):
            raise ValueError("mode must be 'sensitive' or 'precise'")
        self.mode = mode
        cal = Path(calibration or DEFAULT_CALIBRATION)
        if not cal.exists():
            raise FileNotFoundError(f"calibration not found: {cal}")
        blob = json.loads(cal.read_text(encoding="utf-8"))
        if blob.get("mode") != "windowed":
            raise ValueError("this package needs a windowed calibration file")
        self.rules = blob["rules"]
        self.mean = {k: float(v) for k, v in blob["mean"].items()}
        self.std = {k: float(v) for k, v in blob["std"].items()}
        self.voters = list(blob["voters"])
        self.window_thr = float(blob["window"]["essay_thr_1"])
        self.window_words = int(blob.get("window_words", WINDOW_WORDS))
        self.max_windows = int(blob.get("max_windows", MAX_WINDOWS))
        self.n_humans = blob.get("n_humans")
        self.models_dir = Path(models_dir or DEFAULT_MODELS)
        self.device, self.batch_size = device, batch_size
        self._factory = voter_factory or self._default_factory

    def _default_factory(self, key: str):
        d = self.models_dir / MODEL_SUBDIRS[key]
        return StyloVoter(d) if key == "stylo7c" else FastSeqCls(d, batch=self.batch_size, device=self.device)

    def detect(self, texts: list[str] | str) -> list[dict]:
        """-> [{verdict, mode, essay, ens_z, ai_share, windows:[{first_word,last_word,essay,flag}], voters, n_windows}] в порядке входа."""
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return []
        wins = [split_windows(t, self.window_words, self.max_windows) for t in texts]
        raw: dict[str, list] = {}
        for key in self.voters:  # строго по очереди: один голос в памяти
            voter = self._factory(key)
            if key == "stylo7c":
                vals = [float(voter.margins([clean_text(t)])[0]) for t in texts]
            else:
                flat = [clean_text(w[0]) for ws in wins for w in ws]
                out: list[float] = []
                for b in range(0, len(flat), 32):
                    out.extend(float(v) for v in voter.margins(flat[b: b + 32]))
                vals, k = [], 0
                for ws in wins:
                    vals.append(out[k: k + len(ws)])
                    k += len(ws)
            raw[key] = vals
            close = getattr(voter, "close", None)
            if callable(close):
                close()
            del voter
        res = []
        for i in range(len(texts)):
            agg = {"stylo7c": raw["stylo7c"][i], "linda_essay": top25(raw["linda_essay"][i]), "linda_multi_v2": top25(raw["linda_multi_v2"][i])}
            z = sum((agg[k] - self.mean[k]) / self.std[k] for k in self.voters) / len(self.voters)
            ess = agg["linda_essay"]
            wl = [{"first_word": a, "last_word": b, "essay": float(s), "flag": bool(s > self.window_thr)}
                  for (_, a, b), s in zip(wins[i], raw["linda_essay"][i])]
            tot = sum(w["last_word"] - w["first_word"] for w in wl) or 1
            share = sum(w["last_word"] - w["first_word"] for w in wl if w["flag"]) / tot
            res.append({"verdict": verdict(ess, z, agg["stylo7c"], self.rules, self.mode), "mode": self.mode, "essay": float(ess),
                        "ens_z": float(z), "ai_share": float(share), "windows": wl, "voters": agg, "n_windows": len(wl)})
        return res
