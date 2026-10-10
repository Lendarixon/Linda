# -*- coding: utf-8 -*-
"""Linda-Pro 2.0 — маршрутизация по языку: для каждого языка (en / pl / ru) своя тройка голосов Essay + Multi + Stylo (как в 1.x),
пороги из таблицы routing.json (по dev-людям языка). Модели грузятся лениво и по очереди через пул с бюджетом видеопамяти (4 ГБ карты — бюджет ~2.6 ГБ fp16).

score = среднее по голосам (agg - mu) / sd; agg = top25 по окнам ~300 слов (стилометрия — по всему тексту).
  sensitive: ai — score выше порога sensitive (1% ложных на dev-людях языка; EN — 0.7%); uncertain — выше порога 5%; иначе human.
  precise:   ai — score выше порога 0.3%; uncertain — выше порога sensitive.
Результат совместим с LindaPro.detect (verdict, mode, essay, ens_z, ai_share, windows, voters, n_windows) плюс language / score / routing."""
from __future__ import annotations

import json
import re
from pathlib import Path

from .core import MAX_WINDOWS, WINDOW_WORDS, split_windows, top25
from .voters import SpeedOnnx, clean_text

COMPAT = {"essay": "linda_essay", "multi": "linda_multi_v2", "stylo": "stylo7c"}
_PL_LETTERS = re.compile(r"[ąćęłńśźż]", re.I)
_PL_WORDS = re.compile(r"\b(się|jest|nie|oraz|który|która|które|dla|jak|ale|czy|przez|tylko|może|tego|tym)\b", re.I)
_EN_WORDS = re.compile(r"\b(the|and|of|to|is|that|with|for|are|this|which|have)\b", re.I)


def _map_window_tokens(text, window, cleaned, scores, words):
    """Map unchanged window tokens back through split_windows' word joining.

    A changed cleaning result or even one inexact token span discards the whole
    window. The marking pass will read those tokens from the original instead.
    """
    raw, first, last = window
    if cleaned != raw or not 0 <= first <= last <= len(words):
        return []
    original = raw == text and first == 0 and last == len(words)
    if not original:
        selected = words[first:last]
        if " ".join(text[a:b] for a, b in selected) != raw:
            return []
        boundaries = [None] * (len(raw) + 1)
        pos = 0
        for a, b in selected:
            boundaries[pos:pos + b - a + 1] = range(a, b + 1)
            pos += b - a + 1
    mapped = []
    for a, b, *value in scores:
        if not 0 <= a < b <= len(raw):
            return []
        # A short document's window is already the original string. Avoid an
        # identity lookup table proportional to its character count.
        start, end = (a, b) if original else (boundaries[a], boundaries[b])
        if start is None or end is None or text[start:end] != raw[a:b]:
            return []
        mapped.append((start, end, *value))
    return mapped


def detect_language(text: str) -> str:
    """en / pl / ru без внешних библиотек: доля кириллицы; польские буквы и служебные слова против английских."""
    sample = text[:6000]
    letters = [c for c in sample if c.isalpha()]
    if not letters:
        return "en"
    if sum(1 for c in letters if "Ѐ" <= c <= "ӿ") / len(letters) > 0.3:
        return "ru"
    pl = len(_PL_LETTERS.findall(sample)) / len(letters) * 100 + len(_PL_WORDS.findall(sample)) / max(1, len(sample.split())) * 40
    en = len(_EN_WORDS.findall(sample)) / max(1, len(sample.split())) * 40
    return "pl" if pl > 2.0 and pl > en * 0.5 else "en"


class ModelPool:
    """Держит голоса в памяти не больше budget_mb (сумма размеров); при нехватке выгружает давно не использованные."""

    def __init__(self, maker, sizes_mb: dict[str, int], budget_mb: int = 2600):
        self.maker, self.sizes, self.budget = maker, sizes_mb, budget_mb
        self.items: dict[str, object] = {}
        self.order: list[str] = []

    def size(self, key: str) -> int:
        return int(self.sizes.get(key.split("_")[0], 0))

    def get(self, key: str):
        if key in self.items:
            self.order.remove(key)
            self.order.append(key)
            return self.items[key]
        need = self.size(key)
        while self.order and sum(self.size(k) for k in self.items) + need > self.budget:
            old = self.order.pop(0)
            v = self.items.pop(old)
            close = getattr(v, "close", None)
            if callable(close):
                close()
        self.items[key] = self.maker(key)
        self.order.append(key)
        return self.items[key]

    def clear(self) -> None:
        for v in self.items.values():
            close = getattr(v, "close", None)
            if callable(close):
                close()
        self.items, self.order = {}, []


class RoutedLindaPro:
    routed = True
    window_words, max_windows = WINDOW_WORDS, MAX_WINDOWS

    def __init__(self, routing: str | Path | dict, voice_maker, mode: str = "sensitive", budget_mb: int = 2600, pool: ModelPool | None = None, tier: str | None = None):
        if mode not in ("sensitive", "precise"):
            raise ValueError("mode must be 'sensitive' or 'precise'")
        self.table = routing if isinstance(routing, dict) else json.loads(Path(routing).read_text(encoding="utf-8"))
        self.mode = mode
        self.tier_pref = tier
        self.pool = pool or ModelPool(voice_maker, self.table.get("size_mb_fp16", {"essay": 870, "multi": 560}), budget_mb)
        self.cur_lang = "en"
        self.progress = None  # callable(pct, phase): the app shows a progress bar (8..55 % of a check belongs to the voters)
        # merged-таблица: одни и те же модели обслуживают все языки, при смене языка их не выгружаем
        self.shared_voices = self.table.get("kind") == "merged"
        self.voters: list[str] = []  # совместимость с движком: заранее ничего не грузим

    # --- совместимость с engine.py -----------------------------------------------------------------
    def tier(self, lang: str) -> dict:
        tiers = self.table["languages"][lang]["tiers"]
        return tiers.get(self.tier_pref or "full") or next(iter(tiers.values()))

    @property
    def rules(self) -> dict:
        t = self.tier(self.cur_lang)
        r = {k: {"thr_5": t["heat"][k]["thr_5"], "thr_05": t["heat"][k]["thr_05"], "thr_1": t["heat"][k]["thr_1"]} for k in ("essay", "multi")}
        r["ensemble"] = {"thr_5": t["thr_p5"], "thr_1": t["thr_sensitive"], "thr_05": t["thr_p03"]}
        return r

    @property
    def mean(self) -> dict:
        t = self.tier(self.cur_lang)
        return {COMPAT[k]: t["z"][t["heat"][k]["voter"]][0] for k in ("essay", "multi")} | {COMPAT["stylo"]: t["z"][self._stylo_key(t)][0]}

    @property
    def std(self) -> dict:
        t = self.tier(self.cur_lang)
        return {COMPAT[k]: t["z"][t["heat"][k]["voter"]][1] for k in ("essay", "multi")} | {COMPAT["stylo"]: t["z"][self._stylo_key(t)][1]}

    @staticmethod
    def _stylo_key(t: dict) -> str:
        return next(v for v in t["voters"] if v.startswith("stylo"))

    def _factory(self, key: str):
        """linda_essay / linda_multi_v2 (имена 1.x) -> главный голос текущего языка для тепловой карты; настоящие имена голосов работают как есть."""
        t = self.tier(self.cur_lang)
        real = {"linda_essay": t["heat"]["essay"]["voter"], "linda_multi_v2": t["heat"]["multi"]["voter"], "stylo7c": self._stylo_key(t)}.get(key, key)
        return self.pool.get(real)

    # --- анализ ---------------------------------------------------------------------------------------
    def detect(self, texts: list[str] | str) -> list[dict]:
        if isinstance(texts, str):
            texts = [texts]
        out: list[dict | None] = [None] * len(texts)
        langs = [detect_language(t) for t in texts]
        first = True
        for lang in dict.fromkeys(langs):
            if not first and not self.shared_voices:
                self.pool.clear()  # unload previous language voices/sessions before loading next (no simultaneous GPU)
            first = False
            idx = [i for i, x in enumerate(langs) if x == lang]
            for i, r in zip(idx, self._detect_lang(lang, [texts[i] for i in idx])):
                out[i] = r
        if texts:
            self.cur_lang = langs[-1]
        return out  # type: ignore[return-value]

    def close(self) -> None:
        """Unload all pooled voices/sessions."""
        try:
            self.pool.clear()
        except Exception:  # noqa: BLE001
            pass

    def _detect_lang(self, lang: str, texts: list[str]) -> list[dict]:
        self.cur_lang = lang
        t = self.tier(lang)
        wins = [split_windows(x, WINDOW_WORDS, MAX_WINDOWS) for x in texts]
        raw: dict[str, list] = {}
        known = [[] for _ in texts]
        word_offsets = None
        cb = self.progress
        nv = max(1, len(t["voters"]))
        for vi, key in enumerate(t["voters"]):  # строго по очереди: в памяти не больше бюджета
            base, span = 8 + 47 * vi / nv, 47 / nv
            if cb and key not in self.pool.items:
                cb(base, "load")
            voter = self.pool.get(key)
            if cb:
                cb(base, "scan")
            if key.startswith("stylo"):
                raw[key] = [float(voter.margins([clean_text(x)])[0]) for x in texts]
            else:
                flat = [clean_text(w[0]) for ws in wins for w in ws]
                vals: list[float] = []
                capture = self.tier_pref == "speed" and isinstance(voter, SpeedOnnx)
                tokens = []
                for b in range(0, len(flat), 32):
                    if capture:
                        margins, batch_tokens = voter.margins_with_token_scores(flat[b: b + 32])
                        tokens.extend(batch_tokens)
                    else:
                        margins = voter.margins(flat[b: b + 32])
                    vals.extend(float(v) for v in margins)
                    if cb:
                        cb(base + span * min(1.0, (b + 32) / max(1, len(flat))), "scan")
                per, k = [], 0
                for ws in wins:
                    per.append(vals[k: k + len(ws)])
                    k += len(ws)
                raw[key] = per
                if capture and key == t["heat"]["essay"]["voter"]:
                    if word_offsets is None:
                        word_offsets = [[(m.start(), m.end()) for m in re.finditer(r"\S+", x)] for x in texts]
                    k = 0
                    for i, ws in enumerate(wins):
                        for window in ws:
                            known[i].extend(_map_window_tokens(texts[i], window, flat[k], tokens[k], word_offsets[i]))
                            k += 1
        ke, km, ks = t["heat"]["essay"]["voter"], t["heat"]["multi"]["voter"], self._stylo_key(t)
        res = []
        for i in range(len(texts)):
            agg = {k: (raw[k][i] if k.startswith("stylo") else top25(raw[k][i])) for k in t["voters"]}
            wts = t.get("weights")  # merged-таблица: заморозка DEV с весами голосов; без поля — среднее z, как в 2.0
            if wts:
                score = sum(float(wts.get(k, 0.0)) * (agg[k] - t["z"][k][0]) / t["z"][k][1] for k in t["voters"])
            else:
                score = sum((agg[k] - t["z"][k][0]) / t["z"][k][1] for k in t["voters"]) / len(t["voters"])
            ai, hi = (t["thr_p03"], t["thr_sensitive"]) if self.mode == "precise" else (t["thr_sensitive"], t["thr_p5"])
            verdict = "ai" if score > ai else "uncertain" if score > hi else "human"
            thr_w = t["heat"]["essay"]["win_thr_1"]
            wl = [{"first_word": a, "last_word": b, "essay": float(s), "multi": float(m), "flag": bool(s > thr_w)} for (_, a, b), s, m in zip(wins[i], raw[ke][i], raw[km][i])]
            tot = sum(w["last_word"] - w["first_word"] for w in wl) or 1
            share = sum(w["last_word"] - w["first_word"] for w in wl if w["flag"]) / tot
            res.append({"verdict": verdict, "mode": self.mode, "essay": float(agg[ke]), "ens_z": float(score), "score": float(score), "ai_share": float(share), "windows": wl,
                        "voters": {COMPAT["essay"]: agg[ke], COMPAT["multi"]: agg[km], COMPAT["stylo"]: agg[ks]}, "n_windows": len(wl),
                        "language": lang, "routing": {"voters": list(t["voters"]), "config": t.get("config", "")}})
            if self.tier_pref == "speed":
                res[-1]["_lite_token_scores"] = known[i]
        return res
