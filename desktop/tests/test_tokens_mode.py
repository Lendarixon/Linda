"""Token colouring and legacy verdict invariance; synthetic voters, CPU only."""
import re
from types import SimpleNamespace

import numpy as np
import pytest

from linda_desktop import engine as E
from linda_pro.voters import Cancelled, pro_token_scores, FastSeqCls
from linda_desktop.onnx_gpu import OnnxSeqCls
from tools.pro_tok_pack import pack
from tools.tok_eval_engine import summarize


class Voter:
    def __init__(self, folder, available=True, legacy=0., fail=False):
        self.model_dir = folder
        self.has_token_scores = available
        self.legacy, self.fail = legacy, fail

    def margins(self, texts):
        return [self.legacy] * len(texts)

    def token_scores(self, text):
        if self.fail:
            raise ValueError("unavailable graph")
        return [(m.start(), m.end(), 2. if m.group().startswith("High") else 0.)
                for m in re.finditer(r"\S+", text)]


class Detector:
    rules = {k: {"thr_5": 0., "thr_05": 2., "thr_1": 1.} for k in ("essay", "multi", "ensemble")}

    def __init__(self, voter, verdict):
        self.voter, self.verdict = voter, verdict

    def _factory(self, key):
        return self.voter

    def detect(self, texts):
        return [dict(verdict=self.verdict, essay=-1., ens_z=-1.,
                     voters={"linda_essay": -1., "linda_multi_v2": -1.},
                     windows=[dict(first_word=0, last_word=len(texts[0].split()), essay=-1., multi=-1.)])]


def make_engine(monkeypatch, voter, tier, verdict="human", mode="auto"):
    monkeypatch.setattr(E, "gpu_probe", lambda: {})
    monkeypatch.setattr(E, "load_settings", lambda: {"sentences": mode})
    eng = E.Engine()
    eng.tier, eng.device = tier, "cpu"
    eng.dets = {"sensitive": Detector(voter, verdict)}
    return eng


@pytest.mark.parametrize("tier", ["speed", "full"])
@pytest.mark.parametrize("verdict,legacy", [("human", -10.), ("human", 10.), ("ai", -10.), ("uncertain", -10.)])
def test_tokens_mean_and_verdict_invariance(tmp_path, monkeypatch, tier, verdict, legacy):
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=1., scale=.5)
    voter = Voter(tmp_path, legacy=legacy)
    eng = make_engine(monkeypatch, voter, tier, verdict)
    text = "High low. High High."
    assert eng.sentence_mode(4, eng.dets["sensitive"]) == "tokens"
    result = eng.run(text)
    voter.has_token_scores = False
    baseline = eng.run(text)
    for k in ("verdict", "verdict_raised_by", "ens_z", "essay", "voters", "windows", "p_ai"):
        assert result.get(k) == baseline.get(k)
    assert result["sentence_stats"]["granularity"] == "tokens"
    assert baseline["sentence_stats"]["granularity"] == ("context" if tier == "speed" else "hybrid")
    c, s = (0., 1.) if tier == "speed" else (1., .5)
    for sent, mean in zip(result["sentences"], [1., 2.]):
        assert sent["essay_margin"] == sent["multi_margin"] == mean
        assert sent["p_ai"] == sent["essay_prob"] == sent["multi_prob"] == round(E._sig(mean, c, s), 3)
    # Token heads have tier-specific calibration, separate from context mode.
    ai, uncertain = (.815, .35) if tier == "speed" else (.20, .10)
    assert result["sentence_stats"]["thresholds"] == dict(ai=ai, uncertain=uncertain)


@pytest.mark.parametrize("tier", ["speed", "full"])
def test_runtime_fallback_and_explicit_mode(tmp_path, monkeypatch, tier):
    voter = Voter(tmp_path, fail=True)
    eng = make_engine(monkeypatch, voter, tier, mode="tokens")
    result = eng.run("One sentence. Another sentence.")
    assert result["sentence_stats"]["granularity"] == ("context" if tier == "speed" else "hybrid")
    voter.token_scores = lambda text: (_ for _ in ()).throw(Cancelled())
    with pytest.raises(Cancelled):
        eng.run("One sentence.")


def test_explicit_legacy_mode_stays_legacy(tmp_path, monkeypatch):
    eng = make_engine(monkeypatch, Voter(tmp_path), "speed", mode="context")
    assert eng.run("High High.")["sentence_stats"]["granularity"] == "context"


@pytest.mark.parametrize("tier", ["speed", "full"])
@pytest.mark.parametrize("mode", ["auto", "tokens"])
def test_long_text_and_missing_output_fallback(tmp_path, monkeypatch, tier, mode):
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=1., scale=.5)
    voter = Voter(tmp_path)
    eng = make_engine(monkeypatch, voter, tier, mode=mode)
    text = "High low. " * 800
    result = eng.run(text)
    assert result["sentence_stats"]["granularity"] == "tokens"
    assert len(result["sentences"]) == 800
    voter.has_token_scores = False
    baseline = eng.run(text)
    assert baseline["sentence_stats"]["granularity"] == "context"
    for key in ("verdict", "ens_z", "essay", "voters", "windows", "p_ai"):
        assert result.get(key) == baseline.get(key)


@pytest.mark.parametrize("tier", ["speed", "full"])
@pytest.mark.parametrize("scores", [[], [(0, 3, float("nan"))], [(0, 3, 1.)]])
def test_incomplete_or_nonfinite_tokens_fall_back(tmp_path, monkeypatch, tier, scores):
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=0., scale=1.)
    voter = Voter(tmp_path)
    voter.token_scores = lambda text: scores
    eng = make_engine(monkeypatch, voter, tier)
    result = eng.run("One sentence. Another sentence.")
    assert result["sentence_stats"]["granularity"] == ("context" if tier == "speed" else "hybrid")


def test_token_offsets_cross_sentence_boundary(tmp_path, monkeypatch):
    voter = Voter(tmp_path)
    # The spanning token contributes once to each sentence that it touches.
    voter.token_scores = lambda text: [(6, 8, 4.), (2, 6, 2.), (0, 2, 0.)]
    eng = make_engine(monkeypatch, voter, "speed")
    result = eng.run("One. Two.")
    assert result["sentence_stats"]["granularity"] == "tokens"
    assert [s["essay_margin"] for s in result["sentences"]] == [1., 3.]


def test_pro_window_overlap_offsets_and_conv(tmp_path):
    np.savez(tmp_path / "tok_head.npz", w=np.array([1.]), b=0., conv=np.array([1., 2., 3.]), center=0., scale=1.)
    class Tokenizer:
        cls_token_id, sep_token_id = 90, 91
        def __call__(self, text, **kw):
            return dict(input_ids=list(range(1, 9)), offset_mapping=[(i*2, i*2+1) for i in range(8)])
    voter = SimpleNamespace(model_dir=tmp_path, max_len=6, tok=Tokenizer())
    calls = []
    def hidden(seq):
        calls.append(seq)
        return np.array(seq)[:, None]
    scores = pro_token_scores(voter, "x", hidden)
    assert [c[1:-1] for c in calls] == [[1,2,3,4], [4,5,6,7], [7,8]]
    expected = np.zeros(8)
    count = np.zeros(8)
    for start, values in [(0,[1,2,3,4]), (3,[4,5,6,7]), (6,[7,8])]:
        z = np.correlate(np.pad(values,(1,1)), [1,2,3], mode="valid")
        expected[start:start+len(values)] += z
        count[start:start+len(values)] += 1
    np.testing.assert_allclose([x[2] for x in scores], expected/count)
    assert [(a,b) for a,b,_ in scores] == [(i*2,i*2+1) for i in range(8)]


def test_pack_validation_only_and_word_weighting(tmp_path):
    head, feats = tmp_path / "head.npz", tmp_path / "feats.npz"
    np.savez(head, w=np.ones(1), b=0.)
    np.savez(feats, hidden=np.arange(201)[:,None], window_ptr=np.arange(202),
             split=np.array(["val"]*200 + ["train"]), sentence_id=np.arange(201),
             sentence_human_words=np.ones(201))
    center, scale = pack(head, feats, tmp_path / "tok_head.npz")
    assert center == 190. and scale == 4.5
    assert FastSeqCls(tmp_path, device="cpu").has_token_scores
    assert OnnxSeqCls(tmp_path, tmp_path / "cache").has_token_scores


def test_onnx_token_session_is_lazy_and_margins_session_untouched(tmp_path):
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=0., scale=1.)
    voter = OnnxSeqCls(tmp_path, tmp_path / "cache")
    assert voter.tok_sess is None
    sentinel = object()
    voter.sess = sentinel
    class Tok:
        cls_token_id, sep_token_id, pad_token_id = 90, 91, 0
        def __call__(self, text, **kw):
            return dict(input_ids=[1,2], offset_mapping=[(0,1),(2,3)])
    voter.tok = Tok()
    class Session:
        def run(self, outputs, inputs):
            assert outputs == ["last_hidden_state"]
            return [inputs["input_ids"][...,None].astype(np.float32)]
    voter._load_tokens = lambda: setattr(voter, "tok_sess", Session())
    assert voter.token_scores("a b") == [(0,1,1.),(2,3,2.)]
    assert voter.sess is sentinel
    voter.close()
    assert voter.sess is None and voter.tok_sess is None


def test_cpu_token_scores_uses_encoder_without_document_head(tmp_path):
    import torch
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=0., scale=1.)
    voter = FastSeqCls(tmp_path, device="cpu")
    voter.torch, voter.device, voter.args = torch, "cpu", {"input_ids", "attention_mask"}
    class Tok:
        cls_token_id, sep_token_id = 90, 91
        def __call__(self, text, **kw):
            return dict(input_ids=[1,2], offset_mapping=[(0,1),(2,3)])
        def pad(self, enc, **kw):
            ids = torch.tensor(enc["input_ids"])
            return dict(input_ids=ids, attention_mask=torch.ones_like(ids))
    voter.tok = Tok()
    def encoder(**enc):
        return SimpleNamespace(last_hidden_state=enc["input_ids"][...,None].float())
    voter.model = SimpleNamespace(base_model_prefix="deberta", deberta=encoder)
    assert voter.token_scores("a b") == [(0,1,1.), (2,3,2.)]


def test_evaluation_threshold_respects_ties_and_human_budget():
    docs = [dict(kind="mixed_HA", granularity="tokens", words=200, seconds=1.,
                 sents=[dict(w=100, ai=0., p=.6), dict(w=100, ai=1., p=.9)])]
    result = summarize(docs)
    assert result["ai_threshold"] == .9
    assert result["human_ai_share"] == 0.
    assert result["human_uncertain_share"] == 1.
    assert result["mixed_doc_word_accuracy"] == result["ai_word_recall"] == 1.
