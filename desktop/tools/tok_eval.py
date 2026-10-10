"""Evaluate sentence marking using overlapping Lite token scores (CPU only)."""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"

from seg_eval import build
from seg_pick import sig
from linda_desktop.sentences import split_sentences_with_offsets
from linda_pro.voters import SpeedOnnx

ROUTING = Path(r"C:\Users\ninja\AppData\Local\Temp\claude\C--Users-ninja-Desktop---------\78b86c83-004f-42e2-abed-a292aa38d513\scratchpad\mh\calibration\routing.json")


def best_threshold(docs, routing):
    """Use seg_pick's sigmoid, word labels, threshold grid and FP constraints.

    Mixed accuracy is binary word accuracy at the AI threshold: uncertain
    sentences count as non-AI, as described in seg_pick's module docstring.
    """
    probabilities = []
    for doc in docs:
        heat = routing["languages"][doc["lang"]]["tiers"]["speed"]["heat"]["essay"]
        center = heat["thr_5"]
        width = max(1e-3, (heat["thr_05"] - center) / 2)
        probabilities.append([sig(r["tok"], center, width) for r in doc["sents"]])
    best = None
    for threshold in [x / 100 for x in range(40, 96, 2)]:
        acc = defaultdict(float)
        per_lang = defaultdict(lambda: defaultdict(float))
        mixed_correct = mixed_words = 0
        for doc, ps in zip(docs, probabilities):
            for row, probability in zip(doc["sents"], ps):
                label = "ai" if probability >= threshold else "unc" if probability >= 0.35 else "hum"
                truth = "A" if row["ai"] >= 0.5 else "H"
                for counter in (acc, per_lang[doc["lang"]]):
                    counter[truth + "_w"] += row["w"]
                    counter[truth + "_" + label] += row["w"]
                if doc["kind"].startswith("mixed_"):
                    mixed_words += row["w"]
                    mixed_correct += row["w"] * ((label == "ai") == (truth == "A"))
        if not acc["H_w"] or not acc["A_w"]:
            continue
        fp = acc["H_ai"] / acc["H_w"]
        if fp > 0.03 or max(v["H_ai"] / max(1, v["H_w"]) for v in per_lang.values()) > 0.03 * 1.7:
            continue
        recall = acc["A_ai"] / acc["A_w"]
        candidate = {"ai_threshold": threshold, "uncertain": 0.35,
                     "human_ai_share": fp, "ai_word_recall": recall,
                     "mixed_word_accuracy": mixed_correct / mixed_words if mixed_words else None}
        if best is None or recall > best["ai_word_recall"]:
            best = candidate
    return best


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--langs", default="en,ru,pl")
    parser.add_argument("--n-mixed", type=int, default=24)
    parser.add_argument("--n-pure", type=int, default=10)
    parser.add_argument("--routing", type=Path, default=Path(os.environ.get("LINDA_ROUTING", str(ROUTING))))
    args = parser.parse_args()
    langs = [lang.strip() for lang in args.langs.split(",")]
    if args.n_mixed < 0 or args.n_pure < 0 or not langs or any(lang not in ("en", "ru", "pl") for lang in langs):
        parser.error("Use en,ru,pl and non-negative document counts")
    if args.n_mixed + args.n_pure == 0:
        parser.error("At least one document is required")
    routing = json.loads(args.routing.read_text(encoding="utf-8"))
    voter = SpeedOnnx(args.model_dir, threads=4)
    voter._load()
    if "tok" not in {o.name for o in voter.sess.get_outputs()}:
        raise ValueError("Model has no 'tok' output; run lite_tok_export.py first")
    rnd = random.Random(7)
    docs = []
    elapsed = 0.0
    word_count = 0
    try:
        with args.out.open("w", encoding="utf-8") as out:
            for lang in langs:
                for kind, parts in build(lang, args.n_mixed, args.n_pure, rnd):
                    text = "\n\n".join(t for _, t in parts)
                    spans, pos = [], 0
                    for label, part in parts:
                        start = text.index(part, pos)
                        spans.append((start, start + len(part), label))
                        pos = start + len(part)
                    started = time.perf_counter()
                    tokens = voter.token_scores(text)
                    rows = []
                    for sentence in split_sentences_with_offsets(text):
                        scores = [score for start, end, score in tokens
                                  if sentence.start <= start and end <= sentence.end and end > start]
                        if not scores:
                            raise ValueError(f"Sentence has no contained tokens: {lang}/{kind} at {sentence.start}")
                        ai_chars = sum(max(0, min(sentence.end, end) - max(sentence.start, start))
                                       for start, end, label in spans if label == "A")
                        rows.append({"w": max(1, len(sentence.text.split())),
                                     "ai": round(ai_chars / max(1, sentence.end - sentence.start), 3),
                                     "tok": round(sum(scores) / len(scores), 4)})
                    elapsed += time.perf_counter() - started
                    word_count += len(text.split())
                    doc = {"lang": lang, "kind": kind, "tier": "speed", "sents": rows}
                    docs.append(doc)
                    out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    out.flush()
                    print(f"doc={len(docs)} lang={lang} kind={kind} sentences={len(rows)}", flush=True)
    finally:
        voter.close()
    best = best_threshold(docs, routing)
    print(f"docs={len(docs)} words={word_count} sentences={sum(len(d['sents']) for d in docs)}", flush=True)
    if best is None:
        print("best=UNKNOWN: no threshold in seg_pick grid meets human AI share <= 3%", flush=True)
    else:
        accuracy = best["mixed_word_accuracy"]
        accuracy_text = "UNKNOWN" if accuracy is None else f"{accuracy:.6f}"
        print(f"best ai={best['ai_threshold']:.2f} uncertain=0.35 "
              f"human_ai_share={best['human_ai_share']:.6f} "
              f"ai_word_recall={best['ai_word_recall']:.6f} mixed_word_accuracy={accuracy_text}", flush=True)
    print(f"seconds_per_1000_words={elapsed * 1000 / max(1, word_count):.3f} "
          "(tokenization+inference+sentence aggregation; excludes model/data load)", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
