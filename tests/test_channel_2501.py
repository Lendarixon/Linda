# -*- coding: utf-8 -*-
"""Unified verdict+markup channel regression tests for Linda 2.5.0.1."""
from __future__ import annotations

import re
import time

import numpy as np
import pytest

from linda_desktop import engine as E
from test_tokens_mode import Detector, Voter, make_engine


OWNER_EN_SAMPLE = (
    "The model pack 1.5.0 of the Linda desktop application (version 2.5.0.0) introduces "
    "second-generation token-markup heads for all six voice and language pairs, raising "
    "Polish AI recall from 79.43% to 88.86% on the MIGIEL/PolEval 2025 benchmark while "
    "keeping the false positive rate at 2.86%. The updated calibration improves detection "
    "stability across short and medium-length texts without requiring additional GPU memory."
)

PL_HUMAN_SAMPLE = (
    "Wczoraj wieczorem poszedłem na krótki spacer po parku niedaleko mojego domu. "
    "Powietrze było chłodne, ale po całym tygodniu siedzenia przed monitorem dobrze było "
    "wreszcie rozprostować nogi. Po drodze spotkałem sąsiada z psem, zamieniliśmy dwa zdania "
    "o pogodzie i wróciłem zrobić sobie herbatę z cytryną."
)


def _write_schema2_head(folder, voice: str, lang: str, center: float = 3.0, scale: float = 1.6):
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(
        folder / "tok_head.npz",
        w=np.ones(1),
        b=0.0,
        conv=np.ones(1),
        center=np.float64(center),
        scale=np.float64(scale),
        schema=np.int64(2),
        voice=np.str_(voice),
        lang=np.str_(lang),
    )


def _const_voter(folder, token_z: float, legacy: float = -10.0):
    voter = Voter(folder, legacy=legacy)
    voter.token_scores = lambda text: [(m.start(), m.end(), token_z) for m in re.finditer(r"\S+", text)]
    return voter


def test_owner_en_sample_ai_verdict_marks_sentences(tmp_path, monkeypatch):
    """Owner EN sample with p_doc > 0.8 must mark >= 1 sentence as AI even when raw token p_ai < 0.20."""
    # center=3.0, scale=1.6, z=0.0 -> raw sig(0.0, 3.0, 1.6) = 0.133 (below 0.20)
    _write_schema2_head(tmp_path, "essay", "en", center=3.0, scale=1.6)
    voter = _const_voter(tmp_path, token_z=0.0)
    eng = make_engine(monkeypatch, voter, "full", verdict="ai", mode="tokens")
    eng.doc_lang = "en"

    res = eng.run(OWNER_EN_SAMPLE)

    assert res["verdict"] == "ai"
    assert res["p_ai"] > 0.8
    assert res["sentence_stats"]["granularity"] == "tokens"
    assert res["sentence_stats"]["ai"] >= 1
    assert all(s["p_ai"] < 0.20 for s in res["sentences"])
    assert any(s["label"] == "ai" for s in res["sentences"])


@pytest.mark.parametrize("verdict,ens_z", [("human", -1.0), ("uncertain", 1.1)])
def test_pl_human_paragraph_marks_zero_ai(tmp_path, monkeypatch, verdict, ens_z):
    """Polish human paragraph (including borderline uncertain p_doc ~ 0.77) must mark 0% AI sentences."""
    # center=3.64, scale=1.61, z=1.1 -> raw sig(1.1, 3.64, 1.61) ≈ 0.171 (below 0.20, but above old 0.103!)
    _write_schema2_head(tmp_path, "essay", "pl", center=3.64, scale=1.61)
    voter = _const_voter(tmp_path, token_z=1.1)

    class BorderlineDetector(Detector):
        def detect(self, texts):
            out = super().detect(texts)
            out[0]["ens_z"] = ens_z
            out[0]["essay"] = ens_z
            out[0]["language"] = "pl"
            return out

    monkeypatch.setattr(E, "gpu_probe", lambda: {})
    monkeypatch.setattr(E, "load_settings", lambda: {"sentences": "tokens"})
    eng = E.Engine()
    eng.tier, eng.device = "full", "cpu"
    eng.dets = {"sensitive": BorderlineDetector(voter, verdict)}
    eng.doc_lang = "pl"

    res = eng.run(PL_HUMAN_SAMPLE)

    assert res["sentence_stats"]["granularity"] == "tokens"
    assert res["sentence_stats"]["ai"] == 0
    assert res["sentence_stats"]["ai_pct"] == 0


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Hello world.",
        "This is English. To jest polskie zdanie o pogodzie. А это русское предложение для проверки.",
    ],
)
def test_edge_cases_no_crash(tmp_path, monkeypatch, text):
    """Empty, single-sentence, and mixed-language inputs must complete without crashing."""
    _write_schema2_head(tmp_path, "essay", "en", center=3.0, scale=1.6)
    voter = _const_voter(tmp_path, token_z=0.5)
    eng = make_engine(monkeypatch, voter, "full", verdict="human", mode="tokens")
    eng.doc_lang = "en"

    res = eng.run(text)

    assert isinstance(res, dict)
    assert "verdict" in res
    assert isinstance(res.get("sentences"), list)


def test_3000_words_markup_at_most_half_scan(tmp_path, monkeypatch):
    """On a ~3000-word document, batched token markup must stay <= 0.5x scan time."""
    _write_schema2_head(tmp_path, "essay", "en", center=3.0, scale=1.6)
    voter = _const_voter(tmp_path, token_z=4.0)

    def timed_tokens(text):
        time.sleep(0.004)
        return [(m.start(), m.end(), 4.0) for m in re.finditer(r"\S+", text)]

    voter.token_scores = timed_tokens

    class TimedDetector(Detector):
        def detect(self, texts):
            time.sleep(0.06)
            return super().detect(texts)

    monkeypatch.setattr(E, "gpu_probe", lambda: {})
    monkeypatch.setattr(E, "load_settings", lambda: {"sentences": "tokens"})
    eng = E.Engine()
    eng.tier, eng.device = "full", "cpu"
    eng.dets = {"sensitive": TimedDetector(voter, "ai")}
    eng.doc_lang = "en"

    marks: dict[str, float] = {}

    def progress(pct, phase):
        if phase == "scan" and "scan_start" not in marks:
            marks["scan_start"] = time.perf_counter()
        elif phase == "sent" and "scan_end" not in marks:
            marks["scan_end"] = time.perf_counter()
        elif phase == "done":
            marks["done"] = time.perf_counter()

    text = ("The model pack ships updated token heads. " * 430).strip()  # ~3010 words
    assert len(text.split()) >= 3000

    res = eng.run(text, progress=progress)

    scan_s = marks["scan_end"] - marks["scan_start"]
    markup_s = marks["done"] - marks["scan_end"]
    assert res["sentence_stats"]["granularity"] == "tokens"
    assert markup_s <= 0.5 * scan_s, f"markup={markup_s:.4f}s exceeded 0.5 * scan={scan_s:.4f}s"


def test_thr_eff_helper_bounds_and_tier_isolation(tmp_path, monkeypatch):
    """pro_token_thr_eff steers Pro only when p_doc > 0.80, clamped to [0.05, thr], never Lite."""
    assert E.pro_token_thr_eff(0.20, 0.30) == pytest.approx(0.20)
    assert E.pro_token_thr_eff(0.20, 0.80) == pytest.approx(0.20)
    mid = E.pro_token_thr_eff(0.20, 0.85)
    assert 0.05 < mid < 0.20
    assert E.pro_token_thr_eff(0.20, 0.95) == pytest.approx(0.05)
    assert E.pro_token_thr_eff(0.20, 1.00) == pytest.approx(0.05)

    # Lite (tier="speed") must keep raw 0.815 even when verdict="ai" (p_doc >= 0.90)
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0.0, center=0.0, scale=1.0)
    voter = _const_voter(tmp_path, token_z=1.0)  # sig(1.0, 0.0, 1.0) = 0.731 < 0.815
    eng = make_engine(monkeypatch, voter, "speed", verdict="ai", mode="auto")
    res = eng.run("Sentence one. Sentence two.")
    assert res["sentence_stats"]["granularity"] == "tokens"
    assert all(s["label"] == "uncertain" for s in res["sentences"])


def test_owner_report_89pct_auto_falls_back_from_blind_tok_head(tmp_path, monkeypatch):
    """If Pro auto tok_head marks 0 AI on a p_doc > 0.80 text, fall back to document voters (hybrid/context)."""
    report_text = (
        "This report describes model pack 1.5.0 of the Linda desktop application (version 2.5.0.0), a local, "
        "privacy-preserving detector of AI-generated text in English, Polish and Russian that runs on the "
        "user's own computer. The full ensemble is named Linda Assay; the fast CPU student is Linda Loupe. "
        "Pack 1.5.0 keeps the shipped routing_141 verdict pipeline and adds v2 token-level markup heads for "
        "all three languages, raising Polish AI recall from 79.43% to 88.86% on MIGIEL/PolEval 2025."
    )
    _write_schema2_head(tmp_path, "essay", "en", center=3.03, scale=1.61)
    voter = _const_voter(tmp_path, token_z=-1.5, legacy=7.0)  # tok_head ~0.05 (blind), margins +7.0

    class Uncertain89Detector(Detector):
        def detect(self, texts):
            out = super().detect(texts)
            out[0]["ens_z"] = -0.30
            out[0]["essay"] = 7.13
            out[0]["language"] = "en"
            return out

    monkeypatch.setattr(E, "gpu_probe", lambda: {})
    monkeypatch.setattr(E, "load_settings", lambda: {"sentences": "auto"})
    eng = E.Engine()
    eng.tier, eng.device = "full", "cpu"
    eng.dets = {"sensitive": Uncertain89Detector(voter, "uncertain")}
    eng.doc_lang = "en"

    res = eng.run(report_text)

    assert res["p_ai"] > 0.80
    assert res["sentence_stats"]["granularity"] == "hybrid"
    assert res["sentence_stats"]["ai"] >= 1

