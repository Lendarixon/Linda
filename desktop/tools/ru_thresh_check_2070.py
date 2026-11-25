# -*- coding: utf-8 -*-
"""RU threshold re-validation for 2.0.7.0 (audit issue 1 follow-up).

Compares Assay RU-full scores under OLD cleaning (lang='en', as shipped in
1.3.4 calibration) vs NEW cleaning (lang='ru', 2.0.7.0) on held-out RU data:
  - eval/sets/test_ru.jsonl (held-out test split, hum+ai)
  - eval/sets/pool_fpr_ru.jsonl (human FPR pool)

Usage (Linux/Windows, run from Linda_src_2041):
  CPU: python tools/ru_thresh_check_2070.py --device cpu --n-test 30 --n-fpr 60 --out logs/ru_thresh_2070_cpu.json
  GPU: <rocm python> tools/ru_thresh_check_2070.py --device cuda --n-test 30 --n-fpr 60 --out logs/ru_thresh_2070_gpu.json

Stdout is ASCII-only (Windows console); full numbers go to the JSON file.
Voters are scored strictly one by one (DirectML/ROCm safety: no parallel GPU).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

LINDA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LINDA_ROOT))

from linda_pro.core import split_windows, top25  # noqa: E402
from linda_pro.routed import RoutedLindaPro  # noqa: E402
from linda_pro.voters import FastSeqCls, StyloVoter, clean_text  # noqa: E402


def load_jsonl(path: Path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def pick(rows, label, n):
    sel = [r for r in rows if r.get("label") == label][:n]
    return sel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--models-root", default=r"C:\Users\ninja\AppData\Local\Linda-Pro")
    ap.add_argument("--sets-dir", default=r"C:\Users\ninja\Desktop\детектор\eval\sets")
    ap.add_argument("--n-test", type=int, default=30)
    ap.add_argument("--n-fpr", type=int, default=60)
    ap.add_argument("--out", default="logs/ru_thresh_2070.json")
    ap.add_argument("--smoke", action="store_true", help="1 hum + 1 ai only")
    args = ap.parse_args()

    models_root = Path(args.models_root)
    table = json.loads((models_root / "calibration" / "routing.json").read_text(encoding="utf-8"))
    t = table["languages"]["ru"]["tiers"]["full"]
    voice_dirs = table["voice_dirs"]
    models = models_root / "models"
    wts = t.get("weights") or {k: 1.0 / len(t["voters"]) for k in t["voters"]}
    zmean = {k: t["z"][k][0] for k in t["voters"]}
    zsd = {k: t["z"][k][1] for k in t["voters"]}
    thr_s, thr_p5 = t["thr_sensitive"], t["thr_p5"]

    def maker(key: str):
        d = models / voice_dirs[key]
        if key.startswith("stylo"):
            return StyloVoter(d)
        return FastSeqCls(d, batch=8, device=args.device)

    voters = {k: maker(k) for k in t["voters"]}
    ke = t["heat"]["essay"]["voter"]
    km = t["heat"]["multi"]["voter"]
    ks = next(v for v in t["voters"] if v.startswith("stylo"))

    sets_dir = Path(args.sets_dir)
    test_rows = load_jsonl(sets_dir / "test_ru.jsonl")
    fpr_rows = load_jsonl(sets_dir / "pool_fpr_ru.jsonl")
    if args.smoke:
        hum = pick(test_rows, "human", 1)
        ai = pick(test_rows, "ai", 1)
        fpr = fpr_rows[:0]
    else:
        hum = pick(test_rows, "human", args.n_test)
        ai = pick(test_rows, "ai", args.n_test)
        fpr = fpr_rows[: args.n_fpr]
    items = [("test_hum", r) for r in hum] + [("test_ai", r) for r in ai] + [("fpr_hum", r) for r in fpr]
    print(f"items={len(items)} voters={t['voters']} device={args.device}")

    def score(text: str, lang: str):
        wins = split_windows(text, 300, 12)
        per = {}
        v = voters[ks]
        per[ks] = float(v.margins([clean_text(text, lang)])[0])
        for k in t["voters"]:
            if k.startswith("stylo"):
                continue
            flat = [clean_text(w[0], lang) for w in wins]
            vals = []
            vv = voters[k]
            for b in range(0, len(flat), 8):
                vals.extend(float(x) for x in vv.margins(flat[b: b + 8]))
            per[k] = top25(vals)
        z = sum(wts[k] * (per[k] - zmean[k]) / zsd[k] for k in t["voters"])
        verdict = "ai" if z > thr_s else ("uncertain" if z > thr_p5 else "human")
        return per, z, verdict

    t0 = time.time()
    recs = []
    for i, (grp, r) in enumerate(items):
        text = r["text"]
        per_old, z_old, v_old = score(text, "en")
        per_new, z_new, v_new = score(text, "ru")
        recs.append(
            {
                "id": r.get("id"),
                "group": grp,
                "label": r.get("label"),
                "nwords": len(text.split()),
                "z_old": z_old,
                "z_new": z_new,
                "dz": z_new - z_old,
                "v_old": v_old,
                "v_new": v_new,
                "flip": v_old != v_new,
            }
        )
        if (i + 1) % 10 == 0:
            print(f"done {i + 1}/{len(items)} {time.time() - t0:.0f}s")
    for v in voters.values():
        try:
            v.close()
        except Exception:
            pass

    def fpr(rs, key):
        hs = [r for r in rs if r["label"] == "human"]
        bad = [r for r in hs if r[key] != "human"]
        return len(bad) / len(hs) if hs else 0.0

    def tpr(rs, key):
        ais = [r for r in rs if r.get("label") == "ai"]
        hit = [r for r in ais if r[key] == "ai"]
        return len(hit) / len(ais) if ais else 0.0

    import statistics as st

    dz = [r["dz"] for r in recs]
    summary = {
        "device": args.device,
        "n": len(recs),
        "thr_sensitive": thr_s,
        "thr_p5": thr_p5,
        "fpr_old": fpr(recs, "v_old"),
        "fpr_new": fpr(recs, "v_new"),
        "tpr_old": tpr(recs, "v_old"),
        "tpr_new": tpr(recs, "v_new"),
        "mean_dz": sum(dz) / len(dz),
        "max_abs_dz": max(abs(x) for x in dz),
        "flips": sum(1 for r in recs if r["flip"]),
        "flip_ids": [r["id"] for r in recs if r["flip"]][:20],
        "elapsed_s": round(time.time() - t0, 1),
    }
    out = {"summary": summary, "records": recs}
    outp = LINDA_ROOT / args.out
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SUMMARY " + json.dumps(summary, ensure_ascii=True))


if __name__ == "__main__":
    main()
