# -*- coding: utf-8 -*-
"""Detector engine: loads Linda-Pro from the app data folder and produces the result the UI needs (verdict, windows, sentence heat map)."""
from __future__ import annotations

import json
import math
import re
import threading
from pathlib import Path

from . import config
from .sentences import split_sentences_with_offsets

ALL_MODELS = ("linda_essay", "linda_multi_v2", "stylo7c")


def _sig(m: float, c: float, s: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, (m - c) / s))))


def pick_device(pref: str = "auto") -> str:
    if pref in ("cpu", "cuda"):
        return pref
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001
        return "cpu"


class Engine:
    def __init__(self) -> None:
        self.dets: dict | None = None
        self.device = "cpu"
        self.lock = threading.Lock()  # one analysis at a time: the voters share the processor / GPU
        self.state = {"phase": "idle", "error": ""}

    def calibration_file(self) -> Path | None:
        files = sorted((config.data_dir() / "calibration").glob("*.json"))
        return files[0] if files else None

    def unload(self) -> None:
        with self.lock:
            self.dets = None
            self.state = {"phase": "idle", "error": ""}

    def ensure_loaded(self) -> dict:
        if self.dets is not None:
            return self.dets
        cal = self.calibration_file()
        if cal is None:
            raise RuntimeError("model files are not installed yet")
        self.state = {"phase": "loading", "error": ""}
        import linda_pro.core as core
        from linda_pro.server import make_detectors

        core.DEFAULT_MODELS = config.data_dir() / "models"
        core.DEFAULT_CALIBRATION = cal
        settings = load_settings()
        self.device = pick_device(settings.get("device", "auto"))
        try:
            import torch

            torch.set_num_threads(max(1, min(6, (__import__("os").cpu_count() or 4) - 1)))
        except Exception:  # noqa: BLE001
            pass
        dets = make_detectors(self.device)
        for key in dets["sensitive"].voters:  # load every voter now, not on the first request
            v = dets["sensitive"]._factory(key)
            load = getattr(getattr(v, "_v", v), "_load", None)
            if callable(load):
                load()
        self.dets = dets
        self.state = {"phase": "ready", "error": ""}
        return dets

    def info(self) -> dict:
        return {"device": self.device, "phase": self.state["phase"], "error": self.state["error"]}

    CPU_SMOOTH_MAX_WORDS = 700  # automatic mode on a CPU: sliding windows up to this length (about 10 s), longer texts use the fast block colouring
    SMOOTH_WINDOW, SMOOTH_MIN_STEP, SMOOTH_MAX_WINDOWS = 300, 75, 16

    def sentence_mode(self, nwords: int = 0) -> str:
        """smooth = sliding ~300-word windows (the scale the models are calibrated on; boundaries accurate to ~100 words); windows = fast, one score per ~300-word block;
        full = every single sentence on its own (experimental: one sentence is much less reliable than a window)."""
        s = load_settings().get("sentences", "auto")
        if s == "auto":
            return "windows" if self.device != "cuda" and nwords > self.CPU_SMOOTH_MAX_WORDS else "smooth"
        return s if s in ("smooth", "windows", "full") else "smooth"

    def _smooth_windows(self, nwords: int) -> list[tuple[int, int]]:
        W = self.SMOOTH_WINDOW
        if nwords <= W * 1.3:
            return [(0, nwords)]
        step = max(self.SMOOTH_MIN_STEP, -(-(nwords - W) // (self.SMOOTH_MAX_WINDOWS - 1)))
        starts = list(range(0, nwords - W, step)) + [nwords - W]
        return [(s, s + W) for s in starts]

    def run(self, text: str, mode: str = "sensitive", models: list | None = None) -> dict:
        with self.lock:
            dets = self.ensure_loaded()
            det = dets[mode]
            res = det.detect([text])[0]
            R = det.rules

            def par(k, c, s):
                r = R.get(k) or {}
                return (r["thr_5"], max(1.0, (r["thr_05"] - r["thr_5"]) / 2.0)) if "thr_5" in r and "thr_05" in r else (c, s)

            pe_c, pe_s, pm_c, pm_s, ps_c, ps_s = (*par("essay", 6.5, 2.8), *par("multi", 2.5, 2.5), *par("stylo", 1.5, 1.5))
            spans = split_sentences_with_offsets(text)
            selected = set(models) if models else set(ALL_MODELS)
            nwords = len(text.split())
            gran = self.sentence_mode(nwords)
            full = gran == "full"
            m_essay = m_multi = None
            wspans = []  # (first word, after last word, essay margin, multi margin) of the windows used for colouring
            if full and spans:
                s_texts = [s.text for s in spans]
                m_essay = det._factory("linda_essay").margins(s_texts)
                m_multi = det._factory("linda_multi_v2").margins(s_texts)
            elif gran == "smooth" and spans:
                wins = self._smooth_windows(nwords)
                if len(wins) == 1:  # one window: detect() has already scored it
                    w = res["windows"][0]
                    wspans = [(0, nwords, w["essay"], w.get("multi", w["essay"]))]
                else:
                    from linda_pro.voters import clean_text

                    pos = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
                    wt = [clean_text(text[pos[a][0]: pos[b - 1][1]]) for a, b in wins]
                    ce = det._factory("linda_essay").margins(wt)
                    cm = det._factory("linda_multi_v2").margins(wt)
                    wspans = [(a, b, float(e), float(m)) for (a, b), e, m in zip(wins, ce, cm)]
            else:  # fast: sentences inherit the score of their ~300-word block
                wspans = [(w["first_word"], w["last_word"], w["essay"], w.get("multi", w["essay"])) for w in res["windows"]]
            sentences, cnt = [], {"ai": 0, "uncertain": 0, "human": 0}
            for i, s in enumerate(spans):
                if full:
                    me = float(m_essay[i]) if i < len(m_essay) else 0.0
                    mm = float(m_multi[i]) if i < len(m_multi) else 0.0
                    pe, pm = _sig(me, pe_c, pe_s), _sig(mm, pm_c, pm_s)
                    probs = ([pe] if "linda_essay" in selected else []) + ([pm] if "linda_multi_v2" in selected else []) or [pe, pm]
                    p_ai = sum(probs) / len(probs)
                else:
                    wi = len(text[: s.start].split())
                    c = wi + max(1, len(s.text.split())) // 2  # the word in the middle of the sentence
                    cover = [w for w in wspans if w[0] <= c < w[1]] or [min(wspans, key=lambda w: abs((w[0] + w[1]) / 2 - c))]
                    me = sum(w[2] for w in cover) / len(cover)  # average over the windows that cover the sentence
                    mm = sum(w[3] for w in cover) / len(cover)
                    pe, pm = _sig(me, pe_c, pe_s), _sig(mm, pm_c, pm_s)
                    probs = ([pe] if "linda_essay" in selected else []) + ([pm] if "linda_multi_v2" in selected else []) or [pe, pm]
                    p_ai = sum(probs) / len(probs)
                lbl = "ai" if p_ai >= 0.58 else "uncertain" if p_ai >= 0.38 else "human"
                cnt[lbl] += 1
                sentences.append({"start": s.start, "end": s.end, "text": s.text, "essay_margin": round(me, 2), "multi_margin": round(mm, 2),
                                  "essay_prob": round(pe, 3), "multi_prob": round(pm, 3), "p_ai": round(p_ai, 3), "label": lbl})
            res["sentences"] = sentences
            res["sentence_stats"] = {"total": len(sentences), **cnt, "ai_pct": round(cnt["ai"] / len(sentences) * 100) if sentences else 0,
                                     "granularity": {"full": "sentence", "smooth": "smooth", "windows": "window"}[gran]}
            if models and len(models) < 3:
                chosen = [m for m in models if m in det.mean]
                if len(chosen) == 1:
                    name = chosen[0]
                    raw = res["voters"].get(name, 0.0)
                    key, c, s = {"linda_essay": ("essay", pe_c, pe_s), "linda_multi_v2": ("multi", pm_c, pm_s)}.get(name, ("stylo", ps_c, ps_s))
                    v = "ai" if raw >= R[key]["thr_05"] else ("uncertain" if raw >= R[key]["thr_5"] else "human")
                    res["custom_verdict"] = {"model": name, "score": round(raw, 2), "p_ai": round(_sig(raw, c, s), 3), "verdict": v}
                elif len(chosen) > 1:
                    zs = [(res["voters"][k] - det.mean[k]) / det.std[k] for k in chosen if k in res["voters"]]
                    z_sub = sum(zs) / len(zs) if zs else 0.0
                    v = "ai" if z_sub >= R["ensemble"]["thr_1"] else ("uncertain" if z_sub >= R["ensemble"]["thr_5"] else "human")
                    p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, 1.7 * z_sub))))
                    res["custom_verdict"] = {"models": chosen, "z": round(z_sub, 3), "p_ai": round(p, 3), "verdict": v}
            return res


def load_settings() -> dict:
    p = config.data_dir() / "settings.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:  # noqa: BLE001
        return {}


def save_settings(d: dict) -> None:
    (config.data_dir() / "settings.json").write_text(json.dumps(d, indent=1), encoding="utf-8")
