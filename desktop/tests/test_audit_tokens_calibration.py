"""Audit optimizations preserve the existing token calibration, CPU stubs only."""
import numpy as np
import pytest

from test_tokens_mode import Voter, make_engine


@pytest.mark.parametrize("tier,ai,uncertain", [("speed", .815, .35), ("full", .20, .10)])
def test_audit_preserves_token_thresholds_labels_and_verdict(tmp_path, monkeypatch, tier, ai, uncertain):
    np.savez(tmp_path / "tok_head.npz", w=np.ones(1), b=0., center=1., scale=.5)
    voter = Voter(tmp_path)
    eng = make_engine(monkeypatch, voter, tier)
    text = "High low. High High."
    result = eng.run(text)
    voter.has_token_scores = False
    baseline = eng.run(text)
    assert result["sentence_stats"]["thresholds"] == {"ai": ai, "uncertain": uncertain}
    for sentence in result["sentences"]:
        p = sentence["p_ai"]
        assert sentence["label"] == ("ai" if p >= ai else "uncertain" if p >= uncertain else "human")
    for key in ("verdict", "verdict_raised_by", "ens_z", "essay", "voters", "windows", "p_ai"):
        assert result.get(key) == baseline.get(key)
