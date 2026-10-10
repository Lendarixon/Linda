"""Evaluate Engine token sentence marking on the deterministic seg_eval corpus."""
import argparse
import json
import random
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.seg_eval import build
from tools.pro_tok_pack import threshold
import linda_desktop.engine as E


def summarize(docs):
    rows = [s for d in docs for s in d["sents"]]
    p = np.array([s["p"] for s in rows])
    human = np.array([s["w"] * (1 - s["ai"]) for s in rows])
    ai = np.array([s["w"] * s["ai"] for s in rows])
    # AI takes precedence over uncertain, whose fixed lower boundary is .35.
    thr = max(.35, threshold(p, human, .03))
    pred = p >= thr
    mixed = np.array([d["kind"].startswith("mixed") for d in docs for s in d["sents"]])
    # Binary word accuracy at the AI threshold, as in pro_tok_train;
    # report the uncertain band separately.
    correct = human[(~pred) & mixed].sum() + ai[pred & mixed].sum()
    words = (human + ai)[mixed].sum()
    return dict(ai_threshold=thr, uncertain_threshold=.35,
                human_ai_share=float(human[pred].sum() / human.sum()),
                human_uncertain_share=float(human[(p >= .35) & ~pred].sum() / human.sum()),
                ai_word_recall=float(ai[pred].sum() / ai.sum()) if ai.sum() else None,
                mixed_doc_word_accuracy=float(correct / words) if words else None,
                mean_seconds_per_1000_words=float(np.mean([d["seconds"] * 1000 / d["words"] for d in docs])),
                granularity=sorted({d["granularity"] for d in docs}), documents=len(docs))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out", type=Path)
    ap.add_argument("--set", choices=("lite", "pro"), required=True)
    ap.add_argument("--langs", default="en,ru,pl")
    ap.add_argument("--n-mixed", type=int, default=40)
    ap.add_argument("--n-pure", type=int, default=20)
    a = ap.parse_args()
    E.load_settings = lambda: {"sentences": "auto", "quality": a.set, "model_sets": [a.set],
                               "device": "cpu" if a.set == "lite" else "dml"}
    eng, rnd, docs = E.Engine(), random.Random(7), []
    with a.out.open("w", encoding="utf-8") as out:
        for lang in a.langs.split(","):
            for kind, parts in build(lang, a.n_mixed, a.n_pure, rnd):
                text = "\n\n".join(t for _, t in parts)
                spans, pos = [], 0
                for c, t in parts:
                    spans.append((pos, pos + len(t), c))
                    pos += len(t) + 2
                start = time.perf_counter()
                res = eng.run(text, mode="sensitive")
                seconds = time.perf_counter() - start
                rows = []
                for s in res["sentences"]:
                    words = list(re.finditer(r"\S+", text[s["start"]:s["end"]]))
                    truth = sum(sum(max(0, min(s["start"] + w.end(), b) - max(s["start"] + w.start(), a0))
                                    for a0, b, c in spans if c == "A") / (w.end() - w.start()) for w in words)
                    rows.append(dict(w=len(words), ai=truth / max(1, len(words)), p=s["p_ai"]))
                doc = dict(lang=lang, set=a.set, kind=kind, verdict=res["verdict"],
                           granularity=res["sentence_stats"]["granularity"], seconds=seconds,
                           words=len(text.split()), sents=rows)
                docs.append(doc)
                out.write(json.dumps(doc) + "\n")
                out.flush()
                print(f"{lang} {kind}: {seconds:.2f}s granularity={doc['granularity']}", flush=True)
    print(json.dumps(summarize(docs)), flush=True)


if __name__ == "__main__":
    main()
