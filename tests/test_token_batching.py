# -*- coding: utf-8 -*-
"""Batched window inference in pro_token_scores must equal the per-window path.

FastSeqCls.token_scores now plans every window first and runs one forward per batch
of `voter.batch` windows. Coverage, the 25% overlap, the convolution and the
per-token averaging must be unchanged, otherwise token markup would move without
any change to the models. These tests pin that on a stub voter (no model, CPU only);
work/bench_tokens_20261120.md records the same equality on the shipped QA models
(max |diff| 0 over 200/900/3000-word texts, both voices).
"""
import numpy as np
import pytest

from linda_pro import voters as V
from linda_pro.voters import Cancelled, pro_token_scores


class Tokenizer:
    cls_token_id, sep_token_id = 90, 91

    def __init__(self, n=40):
        self.n = n

    def __call__(self, text, **kw):
        n = self.n
        return dict(input_ids=list(range(1, n + 1)),
                    offset_mapping=[(i * 2, i * 2 + 1) for i in range(n)])


def stub_voter(tmp_path, n=40, max_len=8, batch=4):
    np.savez(tmp_path / "tok_head.npz", w=np.array([1.]), b=0.,
             conv=np.array([1., 2., 3.]), center=0., scale=1.)
    return type("V", (), {"model_dir": tmp_path, "max_len": max_len,
                          "batch": batch, "tok": Tokenizer(n)})()


def hidden_fn(calls):
    def hidden(seq):
        calls.append(("one", list(seq)))
        return np.array(seq, dtype=np.float64)[:, None]

    return hidden


def hidden_batch_fn(calls):
    def hidden(seqs):
        assert isinstance(seqs, list) and seqs and isinstance(seqs[0], list)
        calls.append(("batch", [list(s) for s in seqs]))
        return [np.array(s, dtype=np.float64)[:, None] for s in seqs]

    return hidden


@pytest.mark.parametrize("n,max_len,batch", [(40, 8, 4), (40, 8, 1), (40, 6, 3), (5, 8, 4), (40, 8, 64)])
def test_batched_scores_equal_per_window(tmp_path, n, max_len, batch):
    voter = stub_voter(tmp_path, n=n, max_len=max_len, batch=batch)
    one_calls, batch_calls = [], []
    a = pro_token_scores(voter, "x", hidden_fn(one_calls))
    b = pro_token_scores(voter, "x", hidden_fn(one_calls), hidden_batch_fn(batch_calls))
    assert [(x[0], x[1]) for x in a] == [(x[0], x[1]) for x in b]
    np.testing.assert_allclose([x[2] for x in a], [x[2] for x in b], rtol=0, atol=1e-12)
    # Same windows were scored, in the same set; only the packaging differs.
    flat_one = [tuple(c[1]) for c in one_calls]
    flat_batch = [tuple(s) for c in batch_calls for s in c[1]]
    assert sorted(flat_one) == sorted(flat_batch)


def test_batch_size_limits_each_forward(tmp_path):
    voter = stub_voter(tmp_path, n=40, max_len=8, batch=3)
    calls = []
    pro_token_scores(voter, "x", None, hidden_batch_fn(calls))
    assert calls, "batched path must be used"
    assert all(len(c[1]) <= 3 for c in calls), [len(c[1]) for c in calls]
    # 40 tokens, window 6, step 4 (25% overlap) -> 10 windows -> 4 batches of <= 3.
    assert len(calls) == 4


def test_batch_groups_long_windows_apart_from_the_short_tail(tmp_path):
    voter = stub_voter(tmp_path, n=40, max_len=8, batch=8)
    calls = []
    pro_token_scores(voter, "x", None, hidden_batch_fn(calls))
    lengths = [len(s) for c in calls for s in c[1]]
    # Every full window is max_len long, so it must not pad the short tail up.
    assert lengths.count(8) >= 1 and min(lengths) < 8
    full_batches = [[len(s) for s in c[1]] for c in calls]
    assert any(all(l == 8 for l in b) for b in full_batches), full_batches


@pytest.mark.parametrize("batch", [1, 4])
def test_cancel_is_checked_between_batches(tmp_path, monkeypatch, batch):
    voter = stub_voter(tmp_path, n=40, max_len=8, batch=batch)
    calls = []
    monkeypatch.setattr(V, "CANCEL", lambda: len(calls) >= 1)
    with pytest.raises(Cancelled):
        pro_token_scores(voter, "x", None, hidden_batch_fn(calls))
    assert len(calls) == 1


def test_without_the_batch_callable_the_old_path_still_runs(tmp_path):
    """Other voters (OnnxSeqCls) pass only hidden_for_window and must keep working."""
    voter = stub_voter(tmp_path, n=40, max_len=8, batch=4)
    calls = []
    out = pro_token_scores(voter, "x", hidden_fn(calls))
    assert all(c[0] == "one" for c in calls)
    assert len(out) == 40
