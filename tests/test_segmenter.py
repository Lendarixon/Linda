# -*- coding: utf-8 -*-
"""Opt-in one-pass segmenter: DP, long-document windowing, fallback, markup shape."""
import math

import pytest

from linda_desktop import engine
from linda_pro import segmenter as segmod
from linda_pro.segmenter import Segmenter, band, fraction_ai, segments_from_scores, viterbi

RULES = {"essay": {"thr_05": 9.0, "thr_5": 6.0}, "multi": {"thr_05": 9.14, "thr_5": 8.27},
         "stylo": {"thr_05": 3.8, "thr_5": 2.0},
         "ensemble": {"thr_05": 2.0, "thr_1": 1.8, "thr_5": 1.2}}


# --------------------------------------------------------------------------- DP
def test_viterbi_splits_a_clear_mixed_text_into_two_states():
    p = [0.95, 0.96, 0.97, 0.04, 0.03, 0.02]
    words = [10, 10, 10, 10, 10, 10]
    # min_words 25 forbids a one-sentence segment, so the DP must fold neighbours together
    segs = viterbi(p, words, lam=1.0, min_words=25)
    assert [st for _, _, st in segs] == [1, 0]
    assert segs[0][0] == 0 and segs[-1][1] == len(p)
    assert segs[0][1] == 3  # the boundary lands on the first human sentence


def test_whole_human_document_is_one_human_span():
    sents = [(i * 60, i * 60 + 55, "sentence %d with some plain words here." % i) for i in range(4)]
    segs = segments_from_scores(sents, [0.02, 0.03, 0.01, 0.02], lam=1.0, min_words=6)
    assert len(segs) == 1 and segs[0]["label"] == "human" and segs[0]["start"] == 0 and segs[0]["end"] == sents[-1][1]


def test_viterbi_switch_penalty_trades_boundaries_against_noise():
    p = [0.9, 0.2, 0.9, 0.2, 0.9]
    words = [10] * 5

    def switches(pieces):
        return sum(1 for a, b in zip(pieces, pieces[1:]) if a[2] != b[2])

    many = viterbi(p, words, lam=0.0, min_words=1)
    few = viterbi(p, words, lam=1000.0, min_words=1)
    assert switches(many) == 4 and switches(few) == 0


def test_viterbi_min_words_is_a_hard_floor_except_for_a_whole_document():
    # a lone 3-word AI segment is not allowed, so it is grouped with the next sentences
    segs = viterbi([0.95, 0.02, 0.02], [3, 10, 10], lam=0.0, min_words=6)
    assert all(sum([3, 10, 10][i:j]) >= 6 for i, j, _ in segs[:-1])
    # the whole-document exemption keeps a short AI document AI
    assert viterbi([0.95, 0.97], [2, 2], lam=0.0, min_words=6) == [(0, 2, 1)]


def test_bands_are_the_research_cut_offs():
    assert band(0.8) == "ai" and band(0.79) == "unsure"
    assert band(0.1) == "human" and band(0.11) == "unsure"


def test_segments_are_char_weighted_and_cover_the_text():
    sents = [(0, 100, "a " * 20), (101, 130, "b " * 5), (131, 300, "c " * 40)]
    p = [0.95, 0.9, 0.9]
    segs = segments_from_scores(sents, p, lam=1.0, min_words=6)
    assert len(segs) == 1 and segs[0]["start"] == 0 and segs[0]["end"] == 300
    assert segs[0]["label"] == "ai" and 0.9 <= segs[0]["p"] <= 0.96
    assert fraction_ai(segs) == 1.0
    assert set(segs[0]) >= {"start", "end", "label", "p"}


def test_fraction_ai_is_character_weighted():
    segs = [{"start": 0, "end": 900, "state": "human"}, {"start": 900, "end": 1000, "state": "ai"}]
    assert fraction_ai(segs) == pytest.approx(0.1)


# ------------------------------------------------------- long-document windowing
class _StubTok:
    def __init__(self, n):
        self.n = n

    def encode(self, text, add_special_tokens=False):
        class E:
            ids = list(range(1000, 1000 + self.n))
            offsets = [(i * 3, i * 3 + 2) for i in range(self.n)]
        return E()


class _StubSess:
    """Returns one constant probability per call, shaped like the real ai_prob output."""

    def __init__(self):
        self.calls = []

    def run(self, outputs, feeds):
        import numpy as np

        ids = feeds["input_ids"]
        width = ids.shape[1]
        self.calls.append(width)
        return [np.full((1, width), 0.5 + 0.1 * (len(self.calls) - 1), dtype=np.float32)]


def _stub_segmenter(n_tokens, max_len):
    s = Segmenter("does-not-exist", threads=1)
    s.max_len, s._ids = max_len, (2, 1, 0)
    s.tok, s.sess = _StubTok(n_tokens), _StubSess()
    return s


def test_windows_cover_every_token_and_overlap():
    s = Segmenter("does-not-exist", threads=1)
    s.max_len = 66  # 64 content tokens
    w = s._windows(500)
    assert w[0][0] == 0 and w[-1][1] == 500
    assert all(b - a <= 64 for a, b in w)
    covered = [0] * 500
    for a, b in w:
        for i in range(a, b):
            covered[i] += 1
    assert min(covered) >= 1  # no gaps
    assert max(covered) >= 2  # the overlap exists
    assert w[1][0] > w[0][0]  # and moves forward


def test_long_document_averages_token_probabilities_over_windows():
    n, max_len = 200, 66
    s = _stub_segmenter(n, max_len)
    offs, probs = s.token_probs("x" * n)
    assert len(offs) == len(probs) == n
    wins = s._windows(n)
    assert len(wins) > 1
    # window k carries 0.5 + 0.1 * k; a token keeps the mean of its windows
    acc = [0.0] * n
    cnt = [0] * n
    for k, (a, b) in enumerate(wins):
        for i in range(a, b):
            acc[i] += 0.5 + 0.1 * k
            cnt[i] += 1
    for i in range(n):
        assert probs[i] == pytest.approx(acc[i] / cnt[i], abs=1e-6)
    assert len(s.sess.calls) == len(wins)


def test_short_document_is_one_pass():
    s = _stub_segmenter(30, 2048)
    s.token_probs("x" * 30)
    assert len(s.sess.calls) == 1


# ------------------------------------------------------------------ engine side
class FakeDet:
    """Two ~300-word windows: the first human on both models, the second clearly AI."""

    rules = RULES
    mean = {"linda_essay": 0.0, "linda_multi_v2": 0.0, "stylo7c": 0.0}
    std = {"linda_essay": 1.0, "linda_multi_v2": 1.0, "stylo7c": 1.0}

    def detect(self, texts):
        return [{"verdict": "ai", "mode": "sensitive", "essay": 12.0, "ens_z": 2.5, "ai_share": 0.5, "n_windows": 2,
                 "windows": [{"first_word": 0, "last_word": 300, "essay": 1.0, "multi": 0.5, "flag": False},
                             {"first_word": 300, "last_word": 600, "essay": 12.0, "multi": 10.5, "flag": True}],
                 "voters": {"linda_essay": 12.0, "linda_multi_v2": 8.96, "stylo7c": 3.8}}]


class MarkerVoter:
    def margins(self, texts):
        return [1.0 + 11.0 * min(1.0, t.count("AIW") / 150.0) for t in texts]


class StubSeg:
    """Sentence-level segmenter: the second half of the text is AI."""

    def __init__(self, fail=None):
        self.fail = fail
        self.calls = 0

    def run(self, text, sents=None):
        self.calls += 1
        if self.fail:
            raise self.fail
        sents = sents or segmod.split_sentences_with_offsets(text)
        half = len(sents) // 2
        p = [0.02] * half + [0.97] * (len(sents) - half)
        segs = segments_from_scores(sents, p, 1.0, 6, 0.8, 0.1)
        return {"segments": segs, "fraction_ai": fraction_ai(segs), "p_sent": p, "sents": sents}


@pytest.fixture()
def eng(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(tmp_path / "models"))
    e = engine.Engine()
    e.dets = {"sensitive": FakeDet(), "precise": FakeDet()}
    e.device = "cpu"
    e._seg = None
    FakeDet._factory = lambda self, key: MarkerVoter()
    return e


def text_of(n=40):
    return " ".join("Sentence number %d says a plain human thing here today." % i for i in range(n))


def test_missing_model_dir_keeps_the_default_mode(eng, tmp_path):
    engine.save_settings({"sentences": "segmenter"})
    assert eng.segmenter_available() is False
    # no model files: the setting resolves to the default instead of failing
    assert eng.sentence_mode(100) == "hybrid"
    r = eng.run(text_of(), "sensitive")
    assert "segments" not in r and "segmenter_fallback" not in r
    assert r["sentence_stats"]["granularity"] == "hybrid"
    engine.save_settings({"sentences": "auto"})


def test_segmenter_mode_produces_the_same_markup_structure(eng, monkeypatch):
    engine.save_settings({"sentences": "auto"})
    base = eng.run(text_of(), "sensitive")
    engine.save_settings({"sentences": "segmenter"})
    monkeypatch.setattr(engine.Engine, "segmenter_available", lambda self: True)
    stub = StubSeg()
    monkeypatch.setattr(engine.Engine, "segmenter", lambda self, threads=4: stub)
    r = eng.run(text_of(), "sensitive")
    assert stub.calls == 1
    assert r["sentence_stats"]["granularity"] == "segment"
    assert set(r["sentences"][0]) == set(base["sentences"][0])
    assert [(s["start"], s["end"]) for s in r["sentences"]] == [(s["start"], s["end"]) for s in base["sentences"]]
    assert all(s["label"] in ("ai", "uncertain", "human") for s in r["sentences"])
    # the stub labels the second half AI and the first half human
    assert r["sentences"][0]["label"] == "human" and r["sentences"][-1]["label"] == "ai"
    assert r["segments"] and r["segmenter_fraction_ai"] > 0.3
    assert 0 <= r["sentence_stats"]["ai_pct"] <= 100
    engine.save_settings({"sentences": "auto"})


def test_segmenter_error_falls_back_and_says_so(eng, monkeypatch):
    engine.save_settings({"sentences": "segmenter"})
    monkeypatch.setattr(engine.Engine, "segmenter_available", lambda self: True)
    monkeypatch.setattr(engine.Engine, "segmenter", lambda self, threads=4: StubSeg(fail=RuntimeError("graph")))
    r = eng.run(text_of(), "sensitive")
    assert r["segmenter_fallback"] == "RuntimeError"
    assert r["sentence_stats"]["granularity"] == "hybrid"  # the default mode still marks up
    assert r["sentences"] and all(s["label"] in ("ai", "uncertain", "human") for s in r["sentences"])
    engine.save_settings({"sentences": "auto"})
