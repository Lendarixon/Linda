"""Verdict token reuse, original offsets and conservative fallback, CPU stubs."""
import copy
import re
from types import SimpleNamespace

import numpy as np
import pytest

from linda_pro.core import split_windows
from linda_pro.routed import RoutedLindaPro, _map_window_tokens
from linda_pro.voters import Cancelled, SpeedOnnx, clean_text
from test_routed import TIER
from test_tokens_mode import Voter, make_engine


class Tokenizer:
    def encode(self, text, **kwargs):
        chars = [(i, c) for i, c in enumerate(text) if not c.isspace()]
        return SimpleNamespace(ids=[ord(c) + 10 for _, c in chars],
                               offsets=[(i, i + 1) for i, _ in chars])

    def encode_batch(self, texts, **kwargs):
        return [self.encode(text) for text in texts]

    def token_to_id(self, token):
        return {"<s>": 1, "</s>": 2, "<pad>": 0}[token]


class Session:
    def __init__(self, available=True):
        self.calls, self.available = [], available

    def get_outputs(self):
        return [SimpleNamespace(name=n) for n in (["z", "tok"] if self.available else ["z"])]

    def run(self, outputs, inputs):
        self.calls.append((outputs, {k: v.copy() for k, v in inputs.items()}))
        ids, mask = inputs["input_ids"], inputs["attention_mask"]
        z = (ids * mask).sum(axis=1, keepdims=True).astype(np.float32) / 100
        tok = ids.astype(np.float32)
        return [tok] if outputs == ["tok"] else ([z, tok] if self.available else [z])


def speed(tmp_path, n=4, available=True):
    voter = SpeedOnnx(tmp_path, threads=1, batch=2)
    voter.max_len, voter.max_slices, voter.sliced = n + 2, 4, False
    voter.tok, voter.sess, voter.vmap = Tokenizer(), Session(available), None
    return voter


def words(text):
    return [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]


def test_offsets_after_joining_whitespace_and_repeated_unicode_words():
    text = "\told\n\nżółć  żółć\r\nend  "
    window = ("żółć żółć end", 1, 4)
    known = [(0, 4, 1., 10), (5, 9, 2., 11), (10, 13, 3., 12)]
    mapped = _map_window_tokens(text, window, window[0], known, words(text))
    assert [(text[a:b], z, token_id) for a, b, z, token_id in mapped] == [
        ("żółć", 1., 10), ("żółć", 2., 11), ("end", 3., 12)]
    assert [a for a, _, _, _ in mapped] == [6, 12, 18]


def test_whole_original_window_preserves_leading_and_trailing_offsets():
    text = "  hello\nworld  "
    known = [(2, 7, 1., 5), (8, 13, 2., 6)]
    assert _map_window_tokens(text, split_windows(text)[0], text, known, words(text)) == known


@pytest.mark.parametrize("raw", ["hel​lo world", "ｈello world", "аpple world"])
def test_cleaning_change_discards_entire_window(raw):
    assert clean_text(raw) != raw
    assert _map_window_tokens(raw, (raw, 0, 2), clean_text(raw), [(0, 3, 5., 1)], words(raw)) == []


def test_inexact_or_invalid_offset_discards_entire_window():
    text = "one\n\ntwo"
    window = ("one two", 0, 2)
    for bad in [(2, 5, 2., 1), (-1, 2, 2., 1), (0, 99, 2., 1)]:
        assert _map_window_tokens(text, window, window[0], [(0, 3, 1., 1), bad], words(text)) == []
    assert _map_window_tokens(text, ("wrong", 0, 2), "wrong", [], words(text)) == []


@pytest.mark.parametrize("first,last", [(-1, 2), (0, 3), (2, 1)])
def test_invalid_window_word_bounds_fall_back(first, last):
    text = "one two"
    assert _map_window_tokens(text, (text, first, last), text,
                              [(0, 3, 1., 1)], words(text)) == []


def test_capture_keeps_margin_bits_and_identical_inference_batches(tmp_path):
    texts = ["abcdefgh", "x", "żółć", "", "abcdefghijk"]
    voter = speed(tmp_path)
    baseline = voter.margins(texts)
    calls = voter.sess.calls[:]
    voter.sess.calls.clear()
    margins, known = voter.margins_with_token_scores(texts)
    assert np.asarray(margins).tobytes() == np.asarray(baseline).tobytes()
    assert len(calls) == len(voter.sess.calls)
    for (old_outputs, old), (new_outputs, new) in zip(calls, voter.sess.calls):
        assert old_outputs is new_outputs is None
        for key in old:
            np.testing.assert_array_equal(old[key], new[key])
    assert [len(k) for k in known] == [4, 1, 4, 0, 4]
    assert known[0] == [(i, i + 1, float(ord(c) + 10), ord(c) + 10) for i, c in enumerate("abcd")]


def test_invalid_token_output_discards_only_affected_window(tmp_path, monkeypatch):
    voter = speed(tmp_path)
    baseline = voter.margins(["abcd", "xy"])
    run = voter.sess.run

    def invalid_tokens(outputs, inputs):
        z, tok = run(outputs, inputs)
        tok[1, 1] = np.nan  # length sorting puts abcd in the second row
        tok[0, -1] = np.nan  # padding has no character offset to reuse
        return [z, tok]

    monkeypatch.setattr(voter.sess, "run", invalid_tokens)
    margins, known = voter.margins_with_token_scores(["abcd", "xy"])
    assert np.asarray(margins).tobytes() == np.asarray(baseline).tobytes()
    assert known[0] == []
    assert len(known[1]) == 2


def test_gap_pass_never_reads_covered_tokens_and_has_no_overlap(tmp_path):
    voter = speed(tmp_path, n=3)
    text = "abcdefghijklmno"
    known = [(i, i + 1, -float(i), ord(text[i]) + 10) for i in (0, 1, 7, 8, 14)]
    result = voter.token_scores_reuse(text, known)
    read = []
    lengths = []
    for outputs, inputs in voter.sess.calls:
        assert outputs == ["tok"]
        for ids, mask in zip(inputs["input_ids"], inputs["attention_mask"]):
            content = ids[1:int(mask.sum()) - 1].tolist()
            lengths.append(len(content))
            read.extend(content)
    assert lengths == [2, 2, 3, 3]
    assert sorted(read) == sorted(ord(c) + 10 for i, c in enumerate(text) if i not in (0, 1, 7, 8, 14))
    assert [z for _, _, z in result] == [-float(i) if i in (0, 1, 7, 8, 14) else float(ord(c) + 10)
                                        for i, c in enumerate(text)]
    voter.sess.calls.clear()
    assert voter.token_scores_reuse("", []) == []
    voter.token_scores_reuse("ab", known[:2])
    assert voter.sess.calls == []


def test_wrong_token_id_is_read_again_and_duplicate_unicode_offsets_are_distinct(tmp_path):
    voter = speed(tmp_path)
    voter.tok.encode = lambda *a, **kw: SimpleNamespace(ids=[100, 101, 102], offsets=[(0, 1), (0, 1), (1, 2)])
    result = voter.token_scores_reuse("ża", [(0, 1, 7., 100), (0, 1, 8., 101), (1, 2, 9., 999)])
    assert result == [(0, 1, 7.), (0, 1, 8.), (1, 2, 102.)]
    assert voter.sess.calls[0][1]["input_ids"].tolist() == [[1, 102, 2]]


def routed(voter):
    tier = copy.deepcopy(TIER)
    tier["voters"] = ["speed_x", "stylo_x"]
    tier["z"] = {"speed_x": [0., 1.], "stylo_x": [0., 1.]}
    for h in tier["heat"].values():
        h["voter"] = "speed_x"
    table = {"languages": {lang: {"tiers": {"speed": tier}} for lang in ("en", "ru", "pl")}}
    return RoutedLindaPro(table, lambda key: voter if key == "speed_x" else SimpleNamespace(margins=lambda texts: [0.] * len(texts)), tier="speed")


def test_routed_batch_mapping_and_verdict_invariance_with_cleaning_fallback(tmp_path, monkeypatch):
    voter = speed(tmp_path)
    det = routed(voter)
    texts = ["hello world", "hel​lo world", "  repeat\nrepeat  ", "word " * 700] * 9
    reused = det.detect(texts)
    assert reused[0]["_lite_token_scores"]
    assert reused[1]["_lite_token_scores"] == []
    assert reused[2]["_lite_token_scores"]
    assert len(reused[3]["_lite_token_scores"]) == 8
    monkeypatch.setattr(voter, "margins_with_token_scores", lambda texts: (voter.margins(texts), [[] for _ in texts]))
    baseline = det.detect(texts)
    for old, new in zip(baseline, reused):
        old.pop("_lite_token_scores")
        new.pop("_lite_token_scores")
        assert old == new
    # Changed windows fall back to original text, including the invisible char.
    voter.sess.calls.clear()
    result = voter.token_scores_reuse(texts[1], [])
    assert len(result) == len(texts[1].replace(" ", ""))


@pytest.mark.parametrize("tier", ["speed", "full"])
def test_engine_routes_reuse_only_to_lite(tmp_path, monkeypatch, tier):
    if tier == "full":
        np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=0., scale=1.)
    voter = Voter(tmp_path)
    engine = make_engine(monkeypatch, voter, tier, verdict="ai")
    detector = engine.dets["sensitive"]
    original_detect = detector.detect
    known = [(0, 4, 2., 1)]
    def detect(texts):
        result = original_detect(texts)
        result[0]["_lite_token_scores"] = known
        return result
    detector.detect = detect
    calls = []
    def reuse(text, scores):
        calls.append(scores)
        return voter.token_scores(text)
    voter.token_scores_reuse = reuse
    result = engine.run("High low.")
    assert calls == ([known] if tier == "speed" else [])
    assert "_lite_token_scores" not in result
    assert result["sentence_stats"]["granularity"] == "tokens"


def test_reuse_cancellation_and_missing_output(tmp_path, monkeypatch):
    voter = speed(tmp_path, available=False)
    assert voter.margins_with_token_scores(["abc"])[1] == [[]]
    with pytest.raises(ValueError, match="output 'tok'"):
        voter.token_scores_reuse("abc", [])
    voter.sess = Session()
    monkeypatch.setattr("linda_pro.voters.CANCEL", lambda: True)
    with pytest.raises(Cancelled):
        voter.token_scores_reuse("abc", [])


def test_one_changed_window_does_not_discard_other_windows(tmp_path):
    voter = speed(tmp_path)
    det = routed(voter)
    text = " ".join(["hel​lo"] + ["word"] * 699)
    result = det.detect(text)[0]
    known = result["_lite_token_scores"]
    assert len(known) == 4  # first window changed; second window is reusable
    second = words(text)[350][0]
    assert all(a >= second for a, _, _, _ in known)


def test_sliced_verdict_does_not_reuse_inexact_first_slice_offsets(tmp_path):
    voter = speed(tmp_path)
    voter.sliced = True
    baseline = voter.margins(["abcdefghijk"])
    margins, known = voter.margins_with_token_scores(["abcdefghijk"])
    assert margins == baseline
    assert known == [[]]


def test_lite_smoothing_keeps_paragraph_boundaries_and_offsets():
    from linda_desktop.engine import _smooth_lite_tokens

    text = "a b c\n\nd e f"
    scores = [(a, b, z) for (a, b), z in zip(words(text), [0., 0., 12., 12., 12., 12.])]
    result = _smooth_lite_tokens(text, scores, radius=1)
    assert [(a, b) for a, b, _ in result] == words(text)
    assert [z for _, _, z in result] == [0., 4., 8., 12., 12., 12.]
    assert scores[2][2] == 12.  # aggregation never changes captured model outputs
    assert _smooth_lite_tokens("", []) == []
    assert _smooth_lite_tokens("x", [(0, 1, 3.)]) == [(0, 1, 3.)]
    with pytest.raises(ValueError, match="Nonfinite"):
        _smooth_lite_tokens("x", [(0, 1, float("nan"))])


def test_engine_keeps_tokenizer_order_for_duplicate_unicode_offsets(tmp_path, monkeypatch):
    from linda_desktop.engine import _sig, _smooth_lite_tokens
    from linda_desktop.sentences import split_sentences_with_offsets

    voter = speed(tmp_path)
    engine = make_engine(monkeypatch, voter, "speed", verdict="ai")
    text = "Ż b. C d."
    # Two byte tokens for Ż share its character span. Their scores must not
    # decide their sequence positions in the smoothing kernel.
    scores = [(0, 1, 3.), (0, 1, 0.), (2, 3, 0.), (5, 6, 0.)]
    monkeypatch.setattr(voter, "token_scores_reuse", lambda text, known: scores)
    expected = _smooth_lite_tokens(text, scores)
    result = engine.run(text)
    for sentence, span in zip(result["sentences"], split_sentences_with_offsets(text)):
        values = [z for a, b, z in expected if a < span.end and b > span.start]
        mean = sum(values) / len(values)
        assert sentence["essay_margin"] == round(mean, 2)
        assert sentence["p_ai"] == round(_sig(mean, 0., 1.), 3)


def test_lite_human_consistency_does_not_read_sentence_contexts(tmp_path, monkeypatch):
    voter = speed(tmp_path, n=4)
    engine = make_engine(monkeypatch, voter, "speed", verdict="human")
    text = "High low. High High."
    _, known = voter.margins_with_token_scores([text])
    original_detect = engine.dets["sensitive"].detect

    def detect(texts):
        result = original_detect(texts)
        result[0]["_lite_token_scores"] = known[0]
        return result

    engine.dets["sensitive"].detect = detect
    voter.sess.calls.clear()

    def unexpected_context(texts):
        pytest.fail("Lite marking must only read uncovered tokens")

    monkeypatch.setattr(voter, "margins", unexpected_context)
    result = engine.run(text)
    assert result["sentence_stats"]["granularity"] == "tokens"
    assert result["verdict"] == "uncertain"
    assert result["verdict_raised_by"] == "sentences"
    assert all(outputs == ["tok"] for outputs, _ in voter.sess.calls)
    read = [int(t) for _, inputs in voter.sess.calls
            for ids, mask in zip(inputs["input_ids"], inputs["attention_mask"])
            for t in ids[1:int(mask.sum()) - 1]]
    assert sorted(read) == sorted(voter.tok.encode(text).ids[4:])
