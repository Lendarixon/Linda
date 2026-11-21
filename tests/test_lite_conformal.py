# -*- coding: utf-8 -*-
"""Length-binned split-conformal thresholds + abstain for SpeedOnnx (lite voter)."""
import json

from linda_pro.voters import SpeedOnnx

CONF = {
    "bins": [[0, 100], [100, 300], [300, 800], [800, 10**9]],
    "thresholds": [0.88, 0.76, 0.67, 0.80],
    "abstain_margin": 0.05,
}


def _voter(tmp_path, table=CONF):
    if table is not None:
        (tmp_path / "speed_conformal.json").write_text(json.dumps(table), encoding="utf-8")
    return SpeedOnnx(tmp_path)


def test_bin_edges(tmp_path):
    v = _voter(tmp_path)
    assert v.conformal_verdict(1.0, 99) == "ai"          # bin 0, above thr+margin
    assert v.conformal_verdict(1.0, 100) == "ai"         # bin 1 edge
    assert v.conformal_verdict(1.0, 299) == "ai"         # bin 1
    assert v.conformal_verdict(1.0, 300) == "ai"         # bin 2 edge
    assert v.conformal_verdict(1.0, 800) == "ai"         # bin 3 edge
    assert v.conformal_verdict(0.5, 50) == "human"


def test_per_bin_verdict_and_abstain(tmp_path):
    v = _voter(tmp_path)
    # bin 0 thr=0.88, margin 0.05
    assert v.conformal_verdict(0.94, 10) == "ai"         # > 0.93
    assert v.conformal_verdict(0.90, 10) == "uncertain"  # (0.88, 0.93]
    assert v.conformal_verdict(0.88, 10) == "human"      # <= thr
    # bin 1 thr=0.76
    assert v.conformal_verdict(0.82, 150) == "ai"
    assert v.conformal_verdict(0.78, 150) == "uncertain"
    assert v.conformal_verdict(0.70, 150) == "human"


def test_missing_file_fallback_flat(tmp_path):
    v = _voter(tmp_path, table=None)
    assert v.conformal is None
    assert v.conformal_verdict(0.9, 10, flat_thr=0.627) == "ai"
    assert v.conformal_verdict(0.5, 10, flat_thr=0.627) == "human"

