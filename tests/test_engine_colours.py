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


def test_consensus_uses_selected_models_only(eng,monkeypatch):
    FakeDet.window_words,FakeDet.max_windows = 300,12
    class MultiVoter:
        def margins(self,texts):
            return [10.5 if 'Sentence number 59' in text else .5 for text in texts]
    monkeypatch.setattr(FakeDet,'_factory',lambda self,key:MultiVoter(),raising=False)
    both = eng.run(text_of(), "sensitive")["sentences"][-1]["p_ai"]
    only_multi = eng.run(text_of(), "sensitive", ["linda_multi_v2"])["sentences"][-1]["p_ai"]
    assert both > 0.9 and only_multi > 0.9
    assert abs(only_multi - eng.run(text_of(), "sensitive", ["linda_multi_v2"])["sentences"][-1]["multi_prob"]) < 1e-6


def test_auto_mode_is_hybrid(eng):
    engine.save_settings({"sentences": "auto"})
    assert eng.sentence_mode(500) == "hybrid" and eng.sentence_mode(701) == "hybrid"
    eng.device = "cuda"
    assert eng.sentence_mode(1500) == "hybrid" and eng.sentence_mode(9000) == "context" and eng.sentence_mode(300000) == "context"  # длинные тексты: по опорным предложениям
    engine.save_settings({"sentences": "windows"})
    assert eng.sentence_mode(10) == "windows"
    engine.save_settings({"sentences": "full"})
    assert eng.sentence_mode(10) == "full"
    engine.save_settings({"sentences": "smooth"})
    assert eng.sentence_mode(10) == "smooth"
    engine.save_settings({"sentences": "bogus"})
    assert eng.sentence_mode(10) == "hybrid"


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


def test_context_mode_colours_sentence_by_sentence_and_finds_the_boundary(eng):
    FakeDet._factory = lambda self, key: MarkerVoter()
    engine.save_settings({"sentences": "context"})
    human = " ".join("Plain human sentence number %d goes here today." % i for i in range(40))
    ai = " ".join("AIW " * 8 + "sentence %d." % i for i in range(40))
    r = eng.run(human + " " + ai, "sensitive")
    assert r["sentence_stats"]["granularity"] == "context"
    ss = r["sentences"]
    assert [s["label"] for s in ss[:30]] == ["human"] * 30 and [s["label"] for s in ss[-30:]] == ["ai"] * 30
    first_ai = next(i for i, s in enumerate(ss) if s["label"] == "ai")
    assert 33 <= first_ai <= 50  # the switch happens within a few sentences of the real boundary (40), not a 300-word block away


def test_context_anchors_are_capped_and_interpolated(eng):
    sents = ["word " * 9 + "end." for _ in range(1000)]
    anchors, texts = eng._sentence_contexts(sents, 40)
    assert len(anchors) <= 41 and anchors[0] == 0 and anchors[-1] == 999 and len(texts) == len(anchors)
    assert all(100 <= len(t.split()) <= 140 for t in texts)


class IsoLowCtxHigh:
    """A sentence alone looks human (low margin) but inside a window of this text the models say AI: stand-in for a polished AI story."""

    def margins(self, texts):
        return [14.0 if len(t.split()) > 60 else 2.0 for t in texts]


def test_hybrid_shows_a_whole_ai_text_as_ai_not_as_human_sentences(eng):
    FakeDet._factory = lambda self, key: IsoLowCtxHigh()
    engine.save_settings({"sentences": "auto"})
    text = " ".join("A short plain sentence number %d is right here." % i for i in range(40))
    r = eng.run(text, "sensitive")
    st = r["sentence_stats"]
    assert st["granularity"] == "hybrid" and st["thresholds"] == {"ai": 0.72, "uncertain": 0.45}
    assert st["ai"] >= 0.9 * st["total"]  # the context score lifts the sentences that alone would be human
    engine.save_settings({"sentences": "full"})
    assert eng.run(text, "sensitive")["sentence_stats"]["ai"] == 0  # on its own every sentence stays human (the old behaviour)
