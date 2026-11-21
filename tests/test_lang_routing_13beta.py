# -*- coding: utf-8 -*-
"""1.3-beta: EN strictly classic 1.1, PL/RU via routing; switches unload previous pools/sessions."""
from __future__ import annotations

from pathlib import Path

from linda_desktop import engine as engine_mod


class FakePool:
    def __init__(self):
        self.cleared = 0

    def clear(self):
        self.cleared += 1


class FakeDet:
    def __init__(self, tag, lang=None):
        self.tag = tag
        self.pool = FakePool()
        self.cur_lang = lang
        self.closed = 0

    def close(self):
        self.closed += 1


class FakeVoter:
    def __init__(self):
        self.closed = 0

    def margins(self, texts):
        return [0.0] * len(texts)

    def close(self):
        self.closed += 1


def make_engine(monkeypatch, tmp_path):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    e = engine_mod.Engine()
    classic = {"sensitive": FakeDet("classic"), "precise": FakeDet("classic")}
    routed = {"sensitive": FakeDet("routed", "pl"), "precise": FakeDet("routed", "pl")}
    state = {"classic": 0, "routed": 0}

    def ensure_classic(cal):
        state["classic"] += 1
        e.dets = classic
        e._backend = "classic"
        e.state = {"phase": "ready", "error": ""}
        return classic

    def ensure_routed(rt, lang="en"):
        state["routed"] += 1
        e.dets = routed
        e._backend = "routed"
        e.state = {"phase": "ready", "error": ""}
        return routed

    monkeypatch.setattr(e, "_ensure_classic", ensure_classic)
    monkeypatch.setattr(e, "_ensure_routed", ensure_routed)
    monkeypatch.setattr(e, "calibration_file", lambda: tmp_path / "cal.json")
    monkeypatch.setattr(e, "routing_file", lambda: tmp_path / "routing.json")
    return e, classic, routed, state


def test_en_uses_classic_pl_ru_use_routed(monkeypatch, tmp_path):
    e, classic, routed, state = make_engine(monkeypatch, tmp_path)
    assert e.ensure_for_language("en") is classic and e._backend == "classic"
    assert e.ensure_for_language("pl") is routed and e._backend == "routed"
    assert e.ensure_for_language("ru") is routed
    assert state == {"classic": 1, "routed": 1}


def test_switch_unloads_previous_pool_before_next(monkeypatch, tmp_path):
    e, classic, routed, _ = make_engine(monkeypatch, tmp_path)
    e.ensure_for_language("en")
    assert e._backend == "classic"
    e.ensure_for_language("pl")  # classic pool cleared before routed loads
    assert classic["sensitive"].pool.cleared == 1
    assert e._backend == "routed"
    e.ensure_for_language("en")  # routed pool cleared before classic reloads
    assert routed["sensitive"].pool.cleared == 1
    assert e._backend == "classic"


def test_routed_pl_to_ru_clears_previous_language_voices(monkeypatch, tmp_path):
    e, classic, routed, _ = make_engine(monkeypatch, tmp_path)
    e.ensure_for_language("pl")
    e._routed_lang = "pl"
    e.ensure_for_language("ru")
    assert routed["sensitive"].pool.cleared == 1
    assert e._routed_lang == "ru"


def test_run_dispatches_by_text_language(monkeypatch, tmp_path):
    e, classic, routed, _ = make_engine(monkeypatch, tmp_path)
    monkeypatch.setattr(engine_mod, "load_settings", lambda: {"device": "cpu", "sentences": "windows"})
    seen = {}

    def fake_detect(texts):
        lang = "routed" if e._backend == "routed" else "classic"
        seen.setdefault(lang, 0)
        seen[lang] += 1
        return [{"verdict": "human", "mode": "sensitive", "essay": 0.0, "ens_z": -5.0,
                 "ai_share": 0.0, "n_windows": 1,
                 "windows": [{"first_word": 0, "last_word": 60, "essay": -5.0, "multi": -5.0, "flag": False}],
                 "voters": {"linda_essay": -5.0, "linda_multi_v2": -5.0, "stylo7c": -5.0}}]

    for det in (classic["sensitive"], routed["sensitive"]):
        det.detect = fake_detect
        det.rules = {"essay": {"thr_5": 5.0, "thr_05": 9.0}, "multi": {"thr_5": 5.0, "thr_05": 9.0},
                     "stylo": {"thr_5": 5.0, "thr_05": 9.0}, "ensemble": {"thr_5": 1.0, "thr_1": 2.0, "thr_05": 3.0}}
        det.mean = {"linda_essay": 0.0, "linda_multi_v2": 0.0, "stylo7c": 0.0}
        det.std = {"linda_essay": 1.0, "linda_multi_v2": 1.0, "stylo7c": 1.0}
        det.voters = ["linda_essay", "linda_multi_v2", "stylo7c"]
        det._factory = lambda key, _d=det: FakeVoter()
        det.window_words, det.max_windows = 300, 12

    import linda_pro.routed as routed_mod
    monkeypatch.setattr(routed_mod, "detect_language",
                        lambda t: "ru" if "Это" in t else ("pl" if "To jest" in t else "en"))
    en_text = "This is a plain English sentence about the city and its people living there today. " * 8
    ru_text = "Это достаточно длинное русское предложение об истории города и людях которые там живут. " * 8
    pl_text = "To jest dosc dlugie zdanie o historii miasta i ludziach ktorzy tam zyja. " * 8
    e._run_locked(en_text, "sensitive", None)
    assert e._backend == "classic"
    e._run_locked(ru_text, "sensitive", None)
    assert e._backend == "routed"  # switch unloaded classic pool first
    assert classic["sensitive"].pool.cleared >= 1
    e._run_locked(pl_text, "sensitive", None)
    assert e._backend == "routed"
    assert seen.get("classic") == 1 and seen.get("routed") == 2


def test_calibration_file_excludes_routing_json(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    home = tmp_path / "home"
    (home / "calibration").mkdir(parents=True, exist_ok=True)
    (home / "calibration" / "routing.json").write_text("{}", encoding="utf-8")
    (home / "calibration" / "calibration_windowed_v6.json").write_text("{}", encoding="utf-8")
    e = engine_mod.Engine()
    got = e.calibration_file()
    assert got is not None and got.name == "calibration_windowed_v6.json"


def test_ensure_loaded_zero_arg_compatible(monkeypatch, tmp_path):
    e, classic, _, _ = make_engine(monkeypatch, tmp_path)
    e.dets = classic  # manually injected (legacy tests): zero-arg call returns it untouched
    assert e.ensure_loaded() is classic
