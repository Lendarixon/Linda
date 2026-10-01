# -*- coding: utf-8 -*-
"""Heat-map colours in the fast (window) mode: every view uses its own model score, the Multi view is not stuck at zero."""
import pytest

from linda_desktop import engine

RULES = {"essay": {"thr_05": 9.0, "thr_5": 6.0}, "multi": {"thr_05": 9.14, "thr_5": 8.27}, "stylo": {"thr_05": 3.8, "thr_5": 2.0},
         "ensemble": {"thr_05": 2.0, "thr_1": 1.8, "thr_5": 1.2}}


class FakeDet:
    """Two windows of 300 words: the first is human on both models, the second clearly AI on both."""

    rules = RULES
    mean = {"linda_essay": 0.0, "linda_multi_v2": 0.0, "stylo7c": 0.0}
    std = {"linda_essay": 1.0, "linda_multi_v2": 1.0, "stylo7c": 1.0}

    def detect(self, texts):
        return [{"verdict": "ai", "mode": "sensitive", "essay": 12.0, "ens_z": 2.5, "ai_share": 0.5, "n_windows": 2,
                 "windows": [{"first_word": 0, "last_word": 300, "essay": 1.0, "multi": 0.5, "flag": False},
                             {"first_word": 300, "last_word": 600, "essay": 12.0, "multi": 10.5, "flag": True}],
                 "voters": {"linda_essay": 12.0, "linda_multi_v2": 8.96, "stylo7c": 3.8}}]


def text_of(n_sentences=60, words=10):
    return " ".join(("Sentence number %d " % i + "word " * (words - 3)).strip() + "." for i in range(n_sentences))


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    e = engine.Engine()
    e.dets = {"sensitive": FakeDet(), "precise": FakeDet()}
    e.device = "cpu"
    engine.save_settings({"sentences": "windows"})
    return e


def test_windows_mode_gives_each_model_its_own_probability(eng):
    r = eng.run(text_of(), "sensitive")
    ss = r["sentences"]
    assert r["sentence_stats"]["granularity"] == "window" and len(ss) == 60
    first, last = ss[0], ss[-1]
    assert first["label"] == "human" and first["essay_prob"] < 0.1 and first["multi_prob"] < 0.1
    assert last["label"] == "ai" and last["essay_prob"] > 0.9 and last["multi_prob"] > 0.9  # the Multi view is not stuck at 0
    assert last["multi_margin"] == 10.5 and first["multi_margin"] == 0.5
    # about half of the sentences belong to each window
    assert 25 <= r["sentence_stats"]["ai"] <= 35 and 25 <= r["sentence_stats"]["human"] <= 35


def test_consensus_uses_selected_models_only(eng):
    both = eng.run(text_of(), "sensitive")["sentences"][-1]["p_ai"]
    only_multi = eng.run(text_of(), "sensitive", ["linda_multi_v2"])["sentences"][-1]["p_ai"]
    assert both > 0.9 and only_multi > 0.9
    assert abs(only_multi - eng.run(text_of(), "sensitive", ["linda_multi_v2"])["sentences"][-1]["multi_prob"]) < 1e-6


def test_auto_mode_is_sliding_windows(eng):
    engine.save_settings({"sentences": "auto"})
    assert eng.sentence_mode(500) == "smooth" and eng.sentence_mode(700) == "smooth" and eng.sentence_mode(701) == "windows"
    eng.device = "cuda"
    assert eng.sentence_mode(9000) == "smooth"
    engine.save_settings({"sentences": "windows"})
    assert eng.sentence_mode(10) == "windows"
    engine.save_settings({"sentences": "full"})
    assert eng.sentence_mode(10) == "full"
    engine.save_settings({"sentences": "bogus"})
    assert eng.sentence_mode(10) == "smooth"


def test_smooth_window_layout(eng):
    assert eng._smooth_windows(250) == [(0, 250)]
    w = eng._smooth_windows(1000)
    assert w[0] == (0, 300) and w[-1] == (700, 1000) and len(w) <= 16 and all(b - a == 300 for a, b in w)
    assert all(w[i + 1][0] - w[i][0] <= 300 for i in range(len(w) - 1))  # windows overlap, no gaps
    assert len(eng._smooth_windows(8000)) <= 16


class MarkerVoter:
    """Scores a window text by how many 'AIW' marker words it contains (stand-in for the real models)."""

    def margins(self, texts):
        return [1.0 + 11.0 * min(1.0, t.count("AIW") / 150.0) for t in texts]


def test_smooth_mode_finds_the_boundary_within_about_100_words(eng):
    FakeDet._factory = lambda self, key: MarkerVoter()
    engine.save_settings({"sentences": "smooth"})
    human = " ".join("Plain human sentence number %d goes here today." % i for i in range(60))  # ~480 words
    ai = " ".join("AIW AIW AIW AIW AIW AIW sentence %d." % i for i in range(70))  # ~560 words, half of them markers
    ai = " ".join("AIW " * 8 + "sentence %d." % i for i in range(70))
    text = human + " " + ai
    r = eng.run(text, "sensitive")
    assert r["sentence_stats"]["granularity"] == "smooth"
    boundary = len(human)
    far_h = [s for s in r["sentences"] if s["end"] < boundary - 700]
    far_a = [s for s in r["sentences"] if s["start"] > boundary + 700]
    assert far_h and far_a
    assert all(s["label"] == "human" for s in far_h) and all(s["label"] == "ai" for s in far_a)
    assert all(s["multi_prob"] < 0.1 for s in far_h) and all(s["multi_prob"] > 0.9 for s in far_a)  # the Multi view follows its own scores
