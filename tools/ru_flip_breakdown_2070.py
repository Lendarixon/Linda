# -*- coding: utf-8 -*-
"""Per-voter breakdown of RU flips (2.0.7.0 validation). CPU only, ASCII stdout."""
import json
import sys
from pathlib import Path

LINDA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LINDA_ROOT))

from linda_pro.core import split_windows, top25
from linda_pro.voters import FastSeqCls, StyloVoter, clean_text

MODELS = Path(r"C:\Users\ninja\AppData\Local\Linda-Pro")
SETS = Path(r"C:\Users\ninja\Desktop\детектор\eval\sets")
CPU_JSON = LINDA_ROOT / "logs" / "ru_thresh_2070_cpu.json"

table = json.loads((MODELS / "calibration" / "routing.json").read_text(encoding="utf-8"))
t = table["languages"]["ru"]["tiers"]["full"]
vd = table["voice_dirs"]
M = MODELS / "models"
voters = {}
for k in t["voters"]:
    d = M / vd[k]
    voters[k] = StyloVoter(d) if k.startswith("stylo") else FastSeqCls(d, batch=8, device="cpu")
ke = t["heat"]["essay"]["voter"]
km = t["heat"]["multi"]["voter"]
ks = next(v for v in t["voters"] if v.startswith("stylo"))
wts = t.get("weights") or {k: 1.0 / len(t["voters"]) for k in t["voters"]}
zm = {k: t["z"][k][0] for k in t["voters"]}
zs = {k: t["z"][k][1] for k in t["voters"]}

cpu = json.load(open(CPU_JSON, encoding="utf-8"))
want = {r["id"] for r in cpu["records"] if r["flip"]}
rows = {}
for name in ("test_ru.jsonl", "pool_fpr_ru.jsonl"):
    for line in open(SETS / name, encoding="utf-8"):
        o = json.loads(line)
        if o.get("id") in want:
            rows[o["id"]] = o
print(f"flip texts found: {len(rows)}/{len(want)}")


def agg_of(text, lang):
    wins = split_windows(text, 300, 12)
    out = {ks: float(voters[ks].margins([clean_text(text, lang)])[0])}
    for k in t["voters"]:
        if k.startswith("stylo"):
            continue
        flat = [clean_text(w[0], lang) for w in wins]
        vals = []
        for b in range(0, len(flat), 8):
            vals.extend(float(x) for x in voters[k].margins(flat[b: b + 8]))
        out[k] = top25(vals)
    return out


for rid in sorted(want):
    r = rows[rid]
    a_old, a_new = agg_of(r["text"], "en"), agg_of(r["text"], "ru")
    print(f"== {rid} label={r.get('label')} nwords={len(r['text'].split())}")
    for k in t["voters"]:
        zo = (a_old[k] - zm[k]) / zs[k]
        zn = (a_new[k] - zm[k]) / zs[k]
        print(f"  {k}: margin {a_old[k]:+.2f}->{a_new[k]:+.2f} z {zo:+.2f}->{zn:+.2f} dz={zn - zo:+.2f}")
for v in voters.values():
    try:
        v.close()
    except Exception:
        pass
print("DONE")
