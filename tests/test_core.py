# -*- coding: utf-8 -*-
"""Тесты без реальных моделей (поддельные голоса)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linda_pro import LindaPro, split_windows, top25, verdict  # noqa: E402

RULES = {"essay": {"thr_05": 8.0, "thr_1": 7.0, "thr_5": 5.0}, "ensemble": {"thr_05": 2.0, "thr_1": 1.8, "thr_5": 1.4},
         "stylo": {"thr_05": 3.0, "thr_1": 2.5, "thr_5": 1.0}}


def _cal(tmp_path):
    blob = {"mode": "windowed", "window_words": 300, "max_windows": 12, "voters": ["stylo7c", "linda_essay", "linda_multi_v2"],
            "mean": {"stylo7c": 0, "linda_essay": 0, "linda_multi_v2": 0}, "std": {"stylo7c": 1, "linda_essay": 1, "linda_multi_v2": 1},
            "rules": RULES, "window": {"essay_thr_1": 7.0}, "n_humans": 1}
    p = tmp_path / "cal.json"
    p.write_text(json.dumps(blob), encoding="utf-8")
    return p


class Fake:
    def __init__(self, fn):
        self.fn = fn

    def margins(self, texts):
        return [self.fn(t) for t in texts]

    def close(self):
        pass


def test_windows_and_top25():
    assert len(split_windows("w " * 3000)) == 10
    assert len(split_windows("w " * 9000)) == 12
    assert top25([1.0, 2.0, 3.0, 4.0]) == 4.0


def test_verdict_modes():
    assert verdict(9.0, 0.0, 0.0, RULES) == "ai"
    assert verdict(6.0, 0.0, 0.0, RULES) == "uncertain"
    assert verdict(1.0, 0.0, 0.0, RULES) == "human"
    assert verdict(8.0, 0.0, 0.0, RULES, "precise") == "uncertain"      # нет согласия стилометрии
    assert verdict(8.0, 0.0, 1.5, RULES, "precise") == "ai"


def test_detect_with_fake_voters(tmp_path):
    def factory(key):
        return Fake(lambda t: 10.0 if "AIWORD" in t else 0.0) if key == "linda_essay" else Fake(lambda t: 0.0)

    d = LindaPro(calibration=_cal(tmp_path), voter_factory=factory)
    r = d.detect(["plain " * 3000, ("plain " * 300 + "AIWORD ") * 3 + "plain " * 2100])
    assert r[0]["verdict"] == "human" and r[0]["ai_share"] == 0.0
    assert r[1]["n_windows"] == 10 and 0 < r[1]["ai_share"] < 1
    assert d.detect([]) == []


def test_invalid_mode(tmp_path):
    with pytest.raises(ValueError):
        LindaPro(calibration=_cal(tmp_path), mode="x", voter_factory=lambda k: None)
