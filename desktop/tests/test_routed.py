# -*- coding: utf-8 -*-
"""Linda-Pro 2.0: routing by language, the model pool (VRAM budget) and the verdict thresholds (fake voters, no model files needed)."""
from __future__ import annotations

from linda_pro.routed import ModelPool, RoutedLindaPro, detect_language

TIER = {"config": "T", "voters": ["essay_x", "multi_x", "stylo_x"], "mode": "top25",
        "z": {"essay_x": [0.0, 1.0], "multi_x": [0.0, 1.0], "stylo_x": [0.0, 1.0]},
        "sensitive_p": 0.01, "thr_sensitive": 1.0, "thr_p5": 0.3, "thr_p03": 2.0,
        "heat": {"essay": {"voter": "essay_x", "thr_5": 1.0, "thr_05": 3.0, "thr_1": 2.0, "win_thr_1": 2.5},
                 "multi": {"voter": "multi_x", "thr_5": 1.0, "thr_05": 3.0, "thr_1": 2.0, "win_thr_1": 2.5}}}
TABLE = {"size_mb_fp16": {"essay": 870, "multi": 560}, "languages": {lg: {"tiers": {"full": TIER}} for lg in ("en", "pl", "ru")}}


class FakeVoter:
    def __init__(self, key: str, value: float):
        self.key, self.value, self.closed = key, value, False

    def margins(self, texts):
        return [self.value] * len(texts)

    def close(self):
        self.closed = True


def make_det(value: float, mode: str = "sensitive", budget: int = 2600):
    made = []

    def maker(key):
        v = FakeVoter(key, value)
        made.append(v)
        return v

    return RoutedLindaPro(TABLE, maker, mode, budget), made


def test_language_detection():
    assert detect_language("This is a long enough English sentence about the history of the city and the people who live there.") == "en"
    assert detect_language("To jest dość długie zdanie po polsku o historii miasta, które jest ważne dla wszystkich ludzi.") == "pl"
    assert detect_language("Это достаточно длинное русское предложение об истории города и людях, которые там живут.") == "ru"
    assert detect_language("") == "en"


def test_verdict_thresholds_sensitive_and_precise():
    text = "word " * 100
    for value, sens, prec in ((2.5, "ai", "ai"), (1.5, "ai", "uncertain"), (0.5, "uncertain", "human"), (-1.0, "human", "human")):
        det, _ = make_det(value, "sensitive")
        assert det.detect(text)[0]["verdict"] == sens, value
        det, _ = make_det(value, "precise")
        assert det.detect(text)[0]["verdict"] == prec, value


def test_result_is_compatible_with_the_engine():
    det, _ = make_det(3.0)
    r = det.detect("слово " * 120)[0]
    assert r["language"] == "ru" and r["n_windows"] >= 1
    assert set(r["voters"]) == {"linda_essay", "linda_multi_v2", "stylo7c"}
    assert r["windows"][0]["flag"] is True and {"first_word", "last_word", "essay", "multi"} <= set(r["windows"][0])
    assert det.rules["essay"]["thr_5"] == 1.0 and det.rules["ensemble"]["thr_1"] == 1.0
    assert set(det.mean) == {"linda_essay", "linda_multi_v2", "stylo7c"}
    assert det._factory("linda_essay") is det.pool.items["essay_x"]


def test_pool_respects_the_budget_and_closes_evicted_voters():
    det, made = make_det(0.0, budget=1500)  # essay 870 + multi 560 = 1430 fits; a second essay would not
    det.pool.get("essay_x")
    det.pool.get("multi_x")
    assert set(det.pool.items) == {"essay_x", "multi_x"}
    det.pool.get("essay_y")
    assert "essay_x" not in det.pool.items and {v.key: v.closed for v in made}["essay_x"] is True
    assert sum(det.pool.size(k) for k in det.pool.items) <= 1500
