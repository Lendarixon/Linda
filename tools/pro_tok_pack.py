"""Pack HEAD.npz [METRICS.json] [FEATS.npz] into sibling tok_head.npz.

Calibration uses validation sentence means weighted by human words, matching
the head trainer. Tied scores are kept together so FP never exceeds its budget.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linda_pro.voters import apply_token_head


def threshold(scores, weights, rate):
    scores, weights = np.asarray(scores), np.asarray(weights)
    if not len(scores) or weights.sum() <= 0 or not np.isfinite(scores).all():
        raise ValueError("Finite validation scores and human words required")
    order = np.argsort(-scores, kind="stable")
    values = scores[order]
    ends = np.r_[np.flatnonzero(values[1:] != values[:-1]) + 1, len(values)]
    allowed = ends[np.cumsum(weights[order])[ends - 1] <= rate * weights.sum()]
    return float(values[allowed[-1] - 1]) if len(allowed) else float(np.nextafter(values[0], np.inf))


def pack(head_path, feats_path, out_path):
    with np.load(head_path, allow_pickle=False) as f:
        head = {k: f[k].astype(np.float32) for k in ("w", "b")}
        head["conv"] = f["conv"].astype(np.float32) if "conv" in f else np.ones(1, np.float32)
    with np.load(feats_path, allow_pickle=False) as f:
        hidden, ptr, split, sid = f["hidden"], f["window_ptr"], f["split"], f["sentence_id"]
        hwords = f["sentence_human_words"]
        sums, counts = np.zeros(len(hwords)), np.zeros(len(hwords))
        for a, b in zip(ptr[:-1], ptr[1:]):
            if not np.all(split[a:b] == split[a]):
                raise ValueError("Split changes within a window")
            if split[a] != "val":
                continue
            z = apply_token_head(hidden[a:b], head)
            ids = sid[a:b]
            valid = ids >= 0
            np.add.at(sums, ids[valid], z[valid])
            np.add.at(counts, ids[valid], 1)
    present = counts > 0
    scores, weights = sums[present] / counts[present], hwords[present]
    center = threshold(scores, weights, .05)
    strict = threshold(scores, weights, .005)
    scale = max(1e-3, (strict - center) / 2)
    # Scalars stay float64: nextafter thresholds must remain above tied scores.
    with Path(out_path).open("xb") as f:
        np.savez(f, **head, center=np.array(center), scale=np.array(scale))
    return center, scale


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("head", type=Path)
    p.add_argument("extras", nargs="*", type=Path)
    a = p.parse_args()
    if len(a.extras) > 2:
        p.error("Expected optional METRICS.json and FEATS.npz")
    feats = None
    for path in a.extras:
        if path.suffix == ".json":
            json.loads(path.read_text(encoding="utf-8"))
        else:
            feats = path
    feats = feats or a.head.with_name(a.head.stem.removesuffix("_head") + ".npz")
    out = a.head.with_name("tok_head.npz")
    center, scale = pack(a.head, feats, out)
    print(f"Saved {out}: center={center:.6g}, scale={scale:.6g}")


if __name__ == "__main__":
    main()
