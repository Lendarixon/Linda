# -*- coding: utf-8 -*-
"""Detector engine: loads Linda-Pro from the app data folder and produces the result the UI needs (verdict, windows, sentence heat map)."""
from __future__ import annotations

import json
import numpy as np
import math
import os
import re
import subprocess
import threading
from pathlib import Path

from . import config
from .sentences import split_sentences_with_offsets

ALL_MODELS = ("linda_essay", "linda_multi_v2", "stylo7c")


def _sig(m: float, c: float, s: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, (m - c) / s))))


_DISCRETE = re.compile(r"\b(rtx|gtx|geforce|quadro|titan|tesla|radeon rx|radeon pro|radeon vii)\b|\barc\W*(tm\W*)?[ab]\d", re.I)


def _adapter_names() -> list[str]:
    """Names of the graphics adapters (Windows). Cosmetic: shown in the settings."""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_VideoController).Name"], capture_output=True, text=True, timeout=20,
                             creationflags=0x08000000).stdout
        names = [l.strip() for l in out.splitlines() if l.strip() and "basic" not in l.lower()]
        # DirectML нумерует адаптеры «мощные первыми» (device_id 0 = дискретная карта), а Windows перечисляет их в произвольном порядке:
        # без сортировки пункт «RX 9070 XT» в списке мог означать встроенную графику (в 25 раз медленнее)
        return sorted(names, key=lambda n: 0 if _DISCRETE.search(n) else 1)
    except Exception:  # noqa: BLE001
        return []




def gpu_probe() -> dict:
    """Which GPU backend can be used: PyTorch CUDA (NVIDIA) or ROCm (AMD) in development installs, otherwise DirectML through ONNX Runtime (any DirectX 12 card on
    Windows: AMD Radeon, NVIDIA GeForce, Intel Arc), otherwise none. "names" lists every adapter found (used to offer a choice only when there are several)."""
    none = {"available": False, "backend": None, "name": "", "names": [], "discrete": False}
    try:
        import torch

        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            return {"available": True, "backend": "ROCm" if getattr(torch.version, "hip", None) else "CUDA", "name": name, "names": [name], "discrete": True}
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import onnx_gpu

        if onnx_gpu.available():
            names = _adapter_names()
            return {"available": True, "backend": "DirectML", "name": ", ".join(names) or "DirectX 12 graphics card", "names": names, "discrete": any(_DISCRETE.search(n) for n in names)}
    except Exception:  # noqa: BLE001
        pass
    return none


def pick_device(pref: str = "auto") -> str:
    """"cpu", "cuda" (PyTorch CUDA/ROCm) or "dml" (ONNX Runtime DirectML). A GPU choice that cannot be honoured falls back to the CPU instead of failing."""
    if pref == "cpu":
        return "cpu"
    g = gpu_probe()
    if not g["available"] or (pref == "auto" and not g["discrete"]):  # "auto" leaves a lone integrated GPU alone (it can be slower than the CPU); choosing GPU by hand still works
        return "cpu"
    return "dml" if g["backend"] == "DirectML" else "cuda"


class Engine:
    def __init__(self) -> None:
        self.dets: dict | None = None
        self.device = "cpu"
        self.lock = threading.Lock()  # one analysis at a time: the voters share the processor / GPU
        self._jobs: list[dict] = []  # идущие и ожидающие проверки (для отмены)
        self._jobs_lock = threading.Lock()
        self.state = {"phase": "idle", "error": ""}
        self.gpu: dict | None = None  # filled by probe_gpu() in the background (importing torch takes a moment)
        self.gpu_error = ""

    def probe_gpu(self) -> None:
        self.gpu = gpu_probe()

    def calibration_file(self) -> Path | None:
        files = sorted((config.data_dir() / "calibration").glob("*.json"))
        return files[0] if files else None

    def routing_file(self) -> Path | None:
        """Linda-Pro 2.0: table 'language -> three voters + thresholds' (calibration/routing.json, or LINDA_ROUTING for development). Without it the 1.x single-ensemble path is used."""
        env = os.environ.get("LINDA_ROUTING")
        p = Path(env) if env else config.data_dir() / "calibration" / "routing.json"
        return p if p.exists() else None

    def unload(self) -> None:
        with self.lock:
            pool = getattr(getattr(self.dets, "get", lambda k: None)("sensitive"), "pool", None) if self.dets else None
            if pool is not None:
                pool.clear()
            self.dets = None
            self.state = {"phase": "idle", "error": ""}

    def _routed_detectors(self, table_path: Path, settings: dict) -> dict:
        """2.0: per-language voters through one model pool (VRAM budget); fp16 ONNX on DirectML, torch on the CPU."""
        from linda_pro.routed import ModelPool, RoutedLindaPro
        from linda_pro.voters import FastSeqCls, StyloVoter

        table = json.loads(table_path.read_text(encoding="utf-8"))
        models, dirs, cache_dir = config.data_dir() / "models", table["voice_dirs"], config.data_dir() / "onnx"
        idx = int(settings.get("gpu_index", 0) or 0)
        device = self.device

        def make(key: str):
            d = models / dirs[key]
            if key.startswith("stylo"):
                return StyloVoter(d)
            if device == "dml":
                from . import onnx_gpu

                return onnx_gpu.OnnxSeqCls(d, cache_dir, idx, fp16=True)
            return FastSeqCls(d, batch=8, device="cpu")

        budget = int(settings.get("vram_budget_mb", 2600 if device == "dml" else 9000))
        pool = ModelPool(make, table.get("size_mb_fp16", {"essay": 870, "multi": 560}), budget)
        return {"sensitive": RoutedLindaPro(table, make, "sensitive", budget, pool=pool), "precise": RoutedLindaPro(table, make, "precise", budget, pool=pool)}

    def _ensure_routed(self, table_path: Path) -> dict:
        self.state = {"phase": "loading", "error": ""}
        settings = load_settings()
        self.device = pick_device(settings.get("device", "auto"))
        self.gpu_error = ""
        dets = self._routed_detectors(table_path, settings)
        try:  # warm up one transformer now so that a broken GPU path falls back to the CPU here, not in the middle of an analysis
            first = next(k for k in dets["sensitive"].tier("en")["voters"] if not k.startswith("stylo"))
            dets["sensitive"].pool.get(first).margins(["Warm up."])
        except Exception as e:  # noqa: BLE001
            if self.device != "dml":
                raise
            self.gpu_error = f"{type(e).__name__}: {e}"
            self.device = "cpu"
            dets["sensitive"].pool.clear()
            dets = self._routed_detectors(table_path, settings)
        self.dets = dets
        self.state = {"phase": "ready", "error": ""}
        return dets

    def ensure_loaded(self) -> dict:
        if self.dets is not None:
            return self.dets
        rt = self.routing_file()
        if rt is not None:
            return self._ensure_routed(rt)
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
        self.gpu_error = ""
        if self.device == "dml":
            try:
                dets = self._dml_detectors(core, settings)
            except Exception as e:  # noqa: BLE001
                self.gpu_error = f"{type(e).__name__}: {e}"
                self.device = "cpu"
                dets = make_detectors("cpu")
        else:
            dets = make_detectors(self.device)
        try:
            if self.device != 'cpu':
                self._load_voters(dets)
        except Exception as e:  # noqa: BLE001
            if self.device != "dml":
                raise
            self.gpu_error = f"{type(e).__name__}: {e}"  # the GPU path failed (export, driver): use the CPU instead
            self.device = "cpu"
            self.state = {"phase": "loading", "error": "", "note": ""}
            dets = make_detectors("cpu")
            self._load_voters(dets)
        self.dets = dets
        self.state = {"phase": "ready", "error": ""}
        return dets

    def _load_voters(self, dets: dict) -> None:
        if getattr(dets["sensitive"], "routed", False):
            return  # the pool loads voters lazily, per language
        for key in dets["sensitive"].voters:  # load every voter now, not on the first request
            v = dets["sensitive"]._factory(key)
            load = getattr(getattr(v, "_v", v), "_load", None)
            if callable(load):
                load()

    def _dml_detectors(self, core, settings: dict) -> dict:
        """Detectors whose transformer voters run through ONNX Runtime DirectML (the models are exported to ONNX once, in the data folder)."""
        from linda_pro.core import MODEL_SUBDIRS, LindaPro
        from linda_pro.server import _Resident
        from linda_pro.voters import StyloVoter

        from . import onnx_gpu

        cache_dir = config.data_dir() / "onnx"
        idx = int(settings.get("gpu_index", 0) or 0)
        if not (cache_dir / "linda_essay_d" / "model.onnx").exists():
            self.state = {"phase": "loading", "error": "", "note": "Preparing the GPU version of the models (one time, about a minute)..."}
        voters: dict = {}

        def factory(key: str):
            if key not in voters:
                d = Path(core.DEFAULT_MODELS) / MODEL_SUBDIRS[key]
                voters[key] = _Resident(StyloVoter(d) if key == "stylo7c" else onnx_gpu.OnnxSeqCls(d, cache_dir, idx))
            return voters[key]

        base = LindaPro(mode="sensitive", voter_factory=factory)
        base._factory = factory
        return {"sensitive": base, "precise": LindaPro(mode="precise", voter_factory=factory)}

    def info(self) -> dict:
        return {"device": self.device, "phase": self.state["phase"], "error": self.state["error"], "note": self.state.get("note", ""), "gpu": self.gpu, "gpu_error": self.gpu_error}

    # Sentence labels. "ai" stays strict (about 1% of human sentences reach it); "uncertain" is the "possibly AI / mixed" band. A lone sentence is a much weaker
    # input than the ~300-word windows the models were calibrated on, so in the per-sentence mode the band starts lower (about 10% of human sentences fall into
    # it, measured on dev essays); the window-like modes keep the old 0.38.
    AI_THR, UNCERTAIN_THR_SENTENCE, UNCERTAIN_THR_WINDOW = 0.58, 0.25, 0.38
    # (ai, uncertain) thresholds per mode. Hybrid: about 1% and 5% of human sentences reach them (measured on dev essays, whole-human vs whole-AI documents).
    THRESHOLDS = {"hybrid": (0.72, 0.45), "full": (0.58, 0.25)}

    def thresholds(self, gran: str) -> tuple[float, float]:
        return self.THRESHOLDS.get(gran, (self.AI_THR, self.UNCERTAIN_THR_WINDOW))

    def _context_margins(self, det, spans) -> tuple[list[float], list[float]]:
        """Margins of Essay and Multi for every sentence scored in its context (~CONTEXT_WORDS words); between the directly scored anchor sentences the margin is interpolated."""
        from linda_pro.voters import clean_text

        anchors, ctx = self._sentence_contexts([x.text for x in spans], self.CONTEXT_ANCHORS_CPU if self.device == "cpu" else self.CONTEXT_ANCHORS_GPU)
        ctx = [clean_text(t) for t in ctx]
        ae = det._factory("linda_essay").margins(ctx)
        am = det._factory("linda_multi_v2").margins(ctx)
        idx = list(range(len(spans)))
        return [float(v) for v in np.interp(idx, anchors, ae)], [float(v) for v in np.interp(idx, anchors, am)]

    CONTEXT_WORDS = 120                   # size of the neighbourhood scored for each sentence
    CONTEXT_ANCHORS_GPU, CONTEXT_ANCHORS_CPU = 150, 40  # how many sentences are scored directly; the rest are interpolated between them

    def _sentence_contexts(self, sents: list[str], max_anchors: int) -> tuple[list[int], list[str]]:
        """Anchor sentence indices and, for each, the text of the sentence plus neighbours (alternately left and right) up to CONTEXT_WORDS words."""
        n = len(sents)
        wc = [len(x.split()) for x in sents]
        step = max(1, -(-n // max_anchors))
        anchors = list(range(0, n, step))
        if anchors[-1] != n - 1:
            anchors.append(n - 1)
        texts = []
        for i in anchors:
            lo = hi = i
            total, left = wc[i], True
            while total < self.CONTEXT_WORDS and (lo > 0 or hi < n - 1):
                if (left and lo > 0) or hi >= n - 1:
                    lo -= 1
                    total += wc[lo]
                else:
                    hi += 1
                    total += wc[hi]
                left = not left
            texts.append(" ".join(sents[lo: hi + 1]))
        return anchors, texts

    HYBRID_MAX_WORDS = 1500  # автоматический режим: длиннее этого — контекстная подсветка по опорным предложениям
    CPU_SMOOTH_MAX_WORDS = 700  # automatic mode on a CPU: sliding windows up to this length (about 10 s), longer texts use the fast block colouring
    SMOOTH_WINDOW, SMOOTH_MIN_STEP, SMOOTH_MAX_WINDOWS = 300, 75, 16

    def sentence_mode(self, nwords: int = 0) -> str:
        """hybrid (default) = every sentence is scored alone AND in its context and the higher score counts: a lone strongly-AI sentence still lights up, and a whole AI text is no longer shown as human
        sentence by sentence (alone, a sentence is too short for models calibrated on ~300-word windows: on whole-AI essays it flagged about a quarter of the sentences, the context score about 95%);
        context = every sentence is scored together with its neighbours (~CONTEXT_WORDS words around it), so the colour changes sentence by sentence and boundaries are found to the sentence;
        smooth = sliding ~300-word windows (the scale the models are calibrated on; boundaries accurate to ~100 words); windows = fast, one score per ~300-word block;
        full = every single sentence on its own (experimental: one sentence is much less reliable than a window)."""
        s = load_settings().get("sentences", "auto")
        if s == "auto":
            # hybrid оценивает КАЖДОЕ предложение отдельно (на GPU каждое добивается до полного окна), для сотен тысяч слов это минуты и часы;
            # длинные тексты считаем по ~150 опорным предложениям в контексте с интерполяцией — вердикт тот же, подсветка чуть грубее
            return "hybrid" if nwords <= self.HYBRID_MAX_WORDS else "context"
        return s if s in ("hybrid", "full", "context", "smooth", "windows") else "hybrid"

    def _smooth_windows(self, nwords: int) -> list[tuple[int, int]]:
        W = self.SMOOTH_WINDOW
        if nwords <= W * 1.3:
            return [(0, nwords)]
        step = max(self.SMOOTH_MIN_STEP, -(-(nwords - W) // (self.SMOOTH_MAX_WINDOWS - 1)))
        starts = list(range(0, nwords - W, step)) + [nwords - W]
        return [(s, s + W) for s in starts]

    def cancel_cancellable(self) -> int:
        """Прервать все проверки, помеченные как отменяемые (идущие и ожидающие очереди). Возвращает, сколько заданий затронуто."""
        n = 0
        with self._jobs_lock:
            for j in self._jobs:
                if j["cancellable"] and not j["cancel"].is_set():
                    j["cancel"].set()
                    n += 1
        return n

    def run(self, text: str, mode: str = "sensitive", models: list | None = None, cancellable: bool = False, cancel: threading.Event | None = None) -> dict:
        """Одна проверка за раз. cancellable=True: её можно прервать (новый текст в окне одной проверки); пакетные проверки не отменяются."""
        from linda_pro import voters as _voters

        job = {"cancel": cancel if cancel is not None else threading.Event(), "cancellable": cancellable}
        with self._jobs_lock:
            self._jobs.append(job)
        try:
            with self.lock:
                if job["cancel"].is_set():
                    raise _voters.Cancelled()
                _voters.CANCEL = job["cancel"].is_set
                try:
                    result = self._run_locked(text, mode, models)
                    _voters.check_cancel()
                    return result
                finally:
                    _voters.CANCEL = None
        finally:
            with self._jobs_lock:
                if job in self._jobs:
                    self._jobs.remove(job)

    def _run_locked(self, text: str, mode: str = "sensitive", models: list | None = None) -> dict:
        if True:
            chosen_models = list(dict.fromkeys(models or ALL_MODELS))
            if any(name not in ALL_MODELS for name in chosen_models):
                raise ValueError('Unknown model selection')
            if mode == 'precise' and len(chosen_models) < len(ALL_MODELS):
                raise ValueError('Precise mode requires all models.')
            dets = self.ensure_loaded()
            det = dets[mode]
            if getattr(det,'routed',False) and len(chosen_models)<3:
                raise ValueError('This routed calibration requires all models; select all models.')
            if len(chosen_models)==1:
                from .single_model import run as run_single
                return run_single(self,det,text,mode,chosen_models[0])
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
            full = gran in ("hybrid", "full", "context")  # all of them give one margin per sentence
            m_essay = m_multi = None
            wspans = []  # (first word, after last word, essay margin, multi margin) of the windows used for colouring
            if gran == "context" and spans:
                m_essay, m_multi = self._context_margins(det, spans)
            elif gran == "hybrid" and spans:
                s_texts = [x.text for x in spans]
                ie, im = det._factory("linda_essay").margins(s_texts), det._factory("linda_multi_v2").margins(s_texts)
                ce, cm = self._context_margins(det, spans)
                m_essay = [max(float(x), y) for x, y in zip(ie, ce)]  # sigmoid is monotone: the larger margin is the larger probability
                m_multi = [max(float(x), y) for x, y in zip(im, cm)]
            elif full and spans:
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
            thr_ai, thr_unc = self.thresholds(gran)
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
                lbl = "ai" if p_ai >= thr_ai else "uncertain" if p_ai >= thr_unc else "human"
                cnt[lbl] += 1
                sentences.append({"start": s.start, "end": s.end, "text": s.text, "essay_margin": round(me, 2), "multi_margin": round(mm, 2),
                                  "essay_prob": round(pe, 3), "multi_prob": round(pm, 3), "p_ai": round(p_ai, 3), "label": lbl})
            res["sentences"] = sentences
            try:
                res["p_ai"] = verdict_probability(res, R)
            except Exception:  # noqa: BLE001 — отображение не должно ронять проверку
                pass
            res["authorship"] = authorship(res.get("verdict"), sentences)
            res["sentence_stats"] = {"total": len(sentences), **cnt, "ai_pct": round(cnt["ai"] / len(sentences) * 100) if sentences else 0,
                                     "granularity": {"hybrid": "hybrid", "full": "sentence", "context": "context", "smooth": "smooth", "windows": "window"}[gran],
                                     "thresholds": {"ai": thr_ai, "uncertain": thr_unc}}
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
            if res.get('custom_verdict'):
                res['ensemble_reference'] = {k:res.get(k) for k in ('verdict','p_ai','ens_z')}
                custom = res['custom_verdict']
                res['verdict'],res['p_ai'],res['ens_z'] = custom['verdict'],custom['p_ai'],custom.get('z')
                res['authorship'] = authorship(res['verdict'],sentences)
            res['analysis_scope'] = 'subset' if len(chosen_models)<3 else 'ensemble'
            res['models_used'] = chosen_models
            res['models_executed'] = list(ALL_MODELS)
            res['heatmap_available'] = True
            res['ai_share'] = res['authorship']['ai_share']
            return res


def verdict_probability(res: dict, rules: dict) -> float:
    """Вероятность ИИ для показа: 0,5 в начале зоны «неясно» (порог 5% ложных), 0,9 на пороге «ИИ» (0,5% ложных); берётся большая из оценок
    ансамбля и Essay и подгоняется под вердикт (человек < 0,5 <= неясно < 0,9 <= ИИ). Раньше показывалась сигмоида от z без калибровки:
    у человеческих текстов выходило 80-90% «ИИ»."""
    def sig(x: float, c: float, hi: float) -> float:
        k = math.log(9.0) / max(1e-6, hi - c)
        return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, k * (x - c)))))

    n, e = rules.get("ensemble") or {}, rules.get("essay") or {}
    ps = []
    if "ens_z" in res and "thr_5" in n and "thr_05" in n:
        ps.append(sig(float(res["ens_z"]), n["thr_5"], n["thr_05"]))
    if "essay" in res and "thr_5" in e and "thr_05" in e:
        ps.append(sig(float(res["essay"]), e["thr_5"], e["thr_05"]))
    p = max(ps) if ps else 0.5
    v = res.get("verdict")
    if v == "human":
        p = min(p, 0.49)
    elif v == "ai":
        p = max(p, 0.9)
    elif v == "uncertain":
        p = min(max(p, 0.5), 0.89)
    return round(p, 4)


def authorship(verdict: str | None, sentences: list[dict]) -> dict:
    """Document-level authorship from the sentence labels (shares by words) and the calibrated ensemble verdict.

    human = no AI signal worth reporting; ai = the ensemble says AI and most of the text carries an AI or "possibly AI" label;
    mixed = AI shows up in part of the text (or the ensemble is unsure). Sentence-level recall is limited, so the shares are a floor, not an exact split."""
    w = {"ai": 0, "uncertain": 0, "human": 0}
    for x in sentences:
        w[x["label"]] += max(1, len(x["text"].split()))
    tot = sum(w.values()) or 1
    ai, unc, hum = w["ai"] / tot, w["uncertain"] / tot, w["human"] / tot
    n_ai = sum(1 for x in sentences if x["label"] == "ai")
    if verdict == "ai":
        label = "ai" if ai + unc >= 0.5 else "mixed"
    elif verdict == "uncertain":
        label = "mixed"
    else:
        label = "mixed" if ai >= 0.35 and n_ai >= 5 else "human"
    return {"label": label, "ai_share": round(ai, 4), "uncertain_share": round(unc, 4), "human_share": round(hum, 4)}


# Значения интерфейса по умолчанию (задача D + язык из задачи E): хранятся только
# локально в settings.json, применяются фронтом через CSS-переменные и data-атрибуты.
UI_THEMES = ("dark", "light", "contrast")
UI_ACCENTS = ("cobalt", "teal", "purple", "green", "orange")
UI_DENSITIES = ("comfortable", "compact", "spacious")
UI_FONT_SCALES = (90, 100, 110, 125)
UI_RADII = ("square", "soft", "round")
UI_SIDEBARS = ("left", "right", "hidden")
UI_LANGUAGES = ("ru", "pl", "en")

DEFAULT_SETTINGS = {
    "preload": False,
    "theme": "dark", "accent": "cobalt", "density": "comfortable",
    "font_scale": 100, "radius": "square", "sidebar": "left",
    "language": "ru",
}


def load_settings() -> dict:
    """Настройки из settings.json поверх значений по умолчанию (интерфейс + язык)."""
    p = config.data_dir() / "settings.json"
    try:
        stored = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:  # noqa: BLE001
        stored = {}
    if not isinstance(stored, dict):
        stored = {}
    merged = dict(DEFAULT_SETTINGS)
    merged.update(stored)
    return merged


def save_settings(d: dict) -> None:
    import os
    import tempfile
    path = config.data_dir() / 'settings.json'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as out:
        tmp = Path(out.name)
        json.dump(d, out, indent=1)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
