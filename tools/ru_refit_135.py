# -*- coding: utf-8 -*-
"""RU 1.3.5 refit (2.0.7.0 follow-up): same quantile method as
detektor/scripts/build_routing_131.py, but inputs scored with NEW (ru) cleaning.

- mu/sd/weights (z) are KEPT from shipped 1.3.4 (weights untouched).
- thr_sensitive = quantile(xs_dev_hum, 1-0.006547)  [TARGET['ru'] from nollama_report]
- thr_p5/q95, thr_p1/q99, thr_p03/q99.7 of xs_dev_hum
- heat per kind: thr_5=q95, thr_05=q995, thr_1=q99 of per-text agg;
  win_thr_1=q99 of all dev-human window margins.
- Validate on full test_ru.jsonl + first 300 pool_fpr_ru with NEW thresholds.

Writes (repo, NOT live app data):
  calibration_routing_135/routing.json   candidate table (RU full tier replaced)
  logs/ru_refit_135_dev.json             dev scores (agg + window margins)
  logs/ru_refit_135_valid.json           validation verdicts with new thresholds

ASCII stdout only. Voters strictly sequential.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

LINDA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LINDA_ROOT))

import numpy as np  # noqa: E402

from linda_pro.core import split_windows, top25  # noqa: E402
from linda_pro.voters import FastSeqCls, StyloVoter, clean_text  # noqa: E402

RU_TARGET_FPR = 0.006547  # TARGET['ru'] in detektor/scripts/nollama_report.py


def load_jsonl(path: Path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--models-root", default=r"C:\Users\ninja\AppData\Local\Linda-Pro")
    ap.add_argument("--sets-dir", default=r"C:\Users\ninja\Desktop\детектор\eval\sets")
    ap.add_argument("--n-pool", type=int, default=300)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()

    base = Path(args.models_root)
    shipped = json.loads((base / "calibration" / "routing.json").read_text(encoding="utf-8"))
    t_old = shipped["languages"]["ru"]["tiers"]["full"]
    vd = shipped["voice_dirs"]
    M = base / "models"
    voters = {}
    for k in t_old["voters"]:
        d = M / vd[k]
        voters[k] = StyloVoter(d) if k.startswith("stylo") else FastSeqCls(d, batch=8, device=args.device)
    ke = t_old["heat"]["essay"]["voter"]
    km = t_old["heat"]["multi"]["voter"]
    ks = next(v for v in t_old["voters"] if v.startswith("stylo"))
    wts = dict(t_old["weights"])
    zm = {k: t_old["z"][k][0] for k in t_old["voters"]}
    zsd = {k: t_old["z"][k][1] for k in t_old["voters"]}

    sets = Path(args.sets_dir)
    dev = load_jsonl(sets / "dev_ru.jsonl")
    test = load_jsonl(sets / "test_ru.jsonl")
    pool = load_jsonl(sets / "pool_fpr_ru.jsonl")
    if args.smoke:
        dev = [r for r in dev if r.get("label") == "human"][:4] + [r for r in dev if r.get("label") == "ai"][:4]
        test, pool = test[:4], pool[:4]
    print(f"dev={len(dev)} test={len(test)} pool_used={min(len(pool), args.n_pool)} device={args.device}")

    def score_all(rows):
        out = []
        for i, r in enumerate(rows):
            text = r["text"]
            wins = split_windows(text, 300, 12)
            agg = {ks: float(voters[ks].margins([clean_text(text, "ru")])[0])}
            wm = {}
            for k in t_old["voters"]:
                if k.startswith("stylo"):
                    continue
                flat = [clean_text(w[0], "ru") for w in wins]
                vals = []
                for b in range(0, len(flat), 8):
                    vals.extend(float(x) for x in voters[k].margins(flat[b: b + 8]))
                agg[k] = top25(vals)
                wm[k] = vals
            z = sum(wts[k] * (agg[k] - zm[k]) / zsd[k] for k in t_old["voters"])
            out.append({"id": r.get("id"), "label": r.get("label"), "agg": agg, "wins": wm, "z": z})
            if (i + 1) % 50 == 0:
                print(f"scored {i + 1}/{len(rows)}")
        return out

    t0 = time.time()
    dev_sc = score_all(dev)
    devp = LINDA_ROOT / "logs" / "ru_refit_135_dev.json"
    devp.write_text(json.dumps(dev_sc, ensure_ascii=False), encoding="utf-8")

    hum = [s for s in dev_sc if s["label"] == "human"]
    xs = np.array([s["z"] for s in hum])
    new_thr = {
        "thr_sensitive": float(np.quantile(xs, 1 - RU_TARGET_FPR)),
        "thr_p5": float(np.quantile(xs, 0.95)),
        "thr_p1": float(np.quantile(xs, 0.99)),
        "thr_p03": float(np.quantile(xs, 0.997)),
    }
    print("RU new ensemble thresholds: " + json.dumps({k: round(v, 4) for k, v in new_thr.items()}))
    ok = new_thr["thr_p5"] < new_thr["thr_sensitive"] < new_thr["thr_p03"]
    print("order p5<sens<p03:", ok)

    heat = {}
    for kind, key in (("essay", ke), ("multi", km)):
        a = np.array([s["agg"][key] for s in hum])
        w = np.array([m for s in hum for m in s["wins"][key]])
        heat[kind] = {
            "voter": key,
            "thr_5": float(np.quantile(a, 0.95)),
            "thr_05": float(np.quantile(a, 0.995)),
            "thr_1": float(np.quantile(a, 0.99)),
            "win_thr_1": float(np.quantile(w, 0.99)),
        }
        print(kind, json.dumps({k: round(v, 4) for k, v in heat[kind].items() if k != "voter"}))

    # Candidate table: shipped copy, RU full tier thresholds replaced.
    cand = json.loads(json.dumps(shipped, ensure_ascii=False))
    rf = cand["languages"]["ru"]["tiers"]["full"]
    rf.update(new_thr)
    rf["heat"] = heat
    rf["dev_fpr_at_sensitive"] = float((xs > new_thr["thr_sensitive"]).mean())
    rf["n_dev_human"] = len(hum)
    cand["version"] = shipped.get("version", "") + "+ru135cand"
    cand["ru135_note"] = ("RU full tier thresholds refit with NEW (ru) cleaning on dev_ru "
                          "(n_hum=%d); mu/sd/weights unchanged (1.3.4). Candidate only, not applied." % len(hum))
    outdir = LINDA_ROOT / "calibration_routing_135"
    outdir.mkdir(exist_ok=True)
    (outdir / "routing.json").write_text(json.dumps(cand, ensure_ascii=False, indent=1), encoding="utf-8")

    # Validation with NEW thresholds on test + pool subset.
    def verdict(z):
        return "ai" if z > new_thr["thr_sensitive"] else ("uncertain" if z > new_thr["thr_p5"] else "human")

    val_rows = test + pool[: args.n_pool]
    val = []
    for s in score_all(val_rows):
        vnew = verdict(s["z"])
        # old-threshold verdict for contrast (shipped thresholds, new cleaning scores)
        ts, tp = t_old["thr_sensitive"], t_old["thr_p5"]
        vold = "ai" if s["z"] > ts else ("uncertain" if s["z"] > tp else "human")
        val.append({"id": s["id"], "label": s["label"], "z": s["z"], "v_old_thr": vold, "v_new_thr": vnew})
    hs = [v for v in val if v["label"] == "human"]
    ais = [v for v in val if v.get("label") == "ai"]
    summary = {
        "n_hum": len(hs),
        "n_ai": len(ais),
        "fpr_ai_old_thr": sum(1 for v in hs if v["v_old_thr"] == "ai") / len(hs),
        "fpr_ai_new_thr": sum(1 for v in hs if v["v_new_thr"] == "ai") / len(hs),
        "nonhum_old_thr": sum(1 for v in hs if v["v_old_thr"] != "human") / len(hs),
        "nonhum_new_thr": sum(1 for v in hs if v["v_new_thr"] != "human") / len(hs),
        "tpr_old_thr": (sum(1 for v in ais if v["v_old_thr"] == "ai") / len(ais)) if ais else None,
        "tpr_new_thr": (sum(1 for v in ais if v["v_new_thr"] == "ai") / len(ais)) if ais else None,
        "elapsed_s": round(time.time() - t0, 1),
    }
    (LINDA_ROOT / "logs" / "ru_refit_135_valid.json").write_text(
        json.dumps({"summary": summary, "records": val}, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in voters.values():
        try:
            v.close()
        except Exception:
            pass
    print("VALID " + json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
