# -*- coding: utf-8 -*-
"""Таблица kind=merged: веса голосов в score и общие голоса для всех языков."""
from linda_pro.routed import RoutedLindaPro


class Fake:
    def __init__(self, val):
        self.val, self.closed = val, False

    def margins(self, xs):
        return [self.val] * len(xs)

    def close(self):
        self.closed = True


def table():
    tier = {"voters": ["essay_m", "multi_m", "stylo_d"], "mode": "top25",
            "z": {"essay_m": [0.0, 1.0], "multi_m": [0.0, 1.0], "stylo_d": [0.0, 1.0]},
            "weights": {"essay_m": 0.8, "multi_m": 0.0, "stylo_d": 0.2},
            "thr_sensitive": 1.0, "thr_p5": 0.0, "thr_p1": 1.0, "thr_p03": 2.0,
            "heat": {k: {"voter": k + "_m", "thr_5": 0, "thr_05": 1, "thr_1": 1, "win_thr_1": 1} for k in ("essay", "multi")}}
    return {"kind": "merged", "voice_dirs": {}, "languages": {lg: {"tiers": {"full": tier}} for lg in ("en", "pl", "ru")}}


def test_weighted_score_and_shared_voices():
    made = {}

    def maker(key):
        made[key] = Fake({"essay_m": 2.0, "multi_m": 100.0, "stylo_d": 1.0}[key])
        return made[key]

    det = RoutedLindaPro(table(), maker, "sensitive")
    assert det.shared_voices
    r = det.detect(["The quick brown fox jumps over the lazy dog. " * 10, "Съешь ещё этих мягких французских булок. " * 10])
    assert abs(r[0]["score"] - (0.8 * 2.0 + 0.2 * 1.0)) < 1e-9  # multi с весом 0 не двигает вердикт
    assert r[0]["verdict"] == "ai"
    assert all(not v.closed for v in made.values())  # смена языка внутри пачки не выгружает общие голоса
    assert len(made) == 3
