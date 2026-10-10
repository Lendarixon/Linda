"""Build source-disjoint token windows. Labels are half-open character spans.

Only the two speed corpora are used. Missing exclusion files are fatal.
--model-dir overrides the essay tokenizer; default max_len matches FastSeqCls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import unicodedata
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from linda_desktop.sentences import split_sentences_with_offsets

DEFAULT_MODEL = Path(r"C:\Users\ninja\Desktop\Linda_release_1_3_2\pack_1_3_2\models\essay_dhi_131_20261008")
DEFAULT_ROOT = Path(r"C:\Users\ninja\Desktop\детектор")


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def source_hash(text):
    return hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()


def read_jsonl(path):
    with path.open(encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except ValueError as exc:
                    raise ValueError(f"{path}:{line_no}: invalid JSON") from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--n", type=int, default=6000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL)
    p.add_argument("--corpus-root", type=Path, default=DEFAULT_ROOT)
    a = p.parse_args()
    if a.n < 10:
        p.error("--n must be >=10 to include both splits")
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(str(a.model_dir), local_files_only=True, use_fast=True)
    if not tok.is_fast:
        raise ValueError("A fast tokenizer with character offsets is required")
    args = a.model_dir / "train_args.json"
    max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
    budget = max_len - 2
    if budget < 10:
        raise ValueError("max_len is too small")
    drop = json.loads((a.corpus_root / "data/linda/speed_llama_drop.json").read_text(encoding="utf-8-sig"))
    if not isinstance(drop, list) or not all(isinstance(h, str) for h in drop):
        raise ValueError("speed_llama_drop.json must be a list of hashes")
    drop = set(drop)
    eval_files = sorted((a.corpus_root / "eval/sets").glob("*.jsonl"))
    if not eval_files:
        raise FileNotFoundError("No eval/sets/*.jsonl: cannot enforce leakage exclusion")
    prefixes = set()
    for f in eval_files:
        for r in read_jsonl(f):
            if isinstance(r.get("text"), str) and normalized(r["text"]):
                prefixes.add(normalized(r["text"])[:200])
    rows, forbidden, stats = {}, set(), Counter()
    for name in ("speed_corpus.jsonl", "speed_corpus_extra.jsonl"):
        for r in read_jsonl(a.corpus_root / "data/linda" / name):
            text = r.get("text", "")
            if not isinstance(text, str) or not text.strip():
                continue
            key = source_hash(text)
            if r.get("h") in drop:
                forbidden.add(key)
                stats["owner_drop"] += 1
                continue
            if normalized(text)[:200] in prefixes:
                forbidden.add(key)
                stats["eval_drop"] += 1
                continue
            if r.get("lang") not in ("en", "ru", "pl") or r.get("label") not in ("ai", "human"):
                continue
            if key in rows and rows[key]["label"] != r["label"]:
                forbidden.add(key)
                stats["conflicting_label"] += 1
            rows.setdefault(key, dict(text=text.strip(), lang=r["lang"], label=r["label"],
                                      h=r.get("h"), src=r.get("src")))
    for key in forbidden:
        rows.pop(key, None)
    # Group exact/normalized duplicate texts before stratified deterministic 90/10 assignment.
    groups = defaultdict(list)
    for key, r in rows.items():
        groups[r["lang"], r["label"]].append(key)
    pools = defaultdict(list)
    for (lang, label), keys in groups.items():
        keys.sort(key=lambda k: hashlib.sha256(f"{a.seed}:{k}".encode()).digest())
        nv = max(1, round(len(keys) * .1)) if len(keys) >= 2 else 0
        for i, key in enumerate(keys):
            pools["val" if i < nv else "train", lang, label].append(key)
    langs = [l for l in ("en", "ru", "pl") if all(pools[s, l, c] for s in ("train", "val") for c in ("ai", "human"))]
    if not langs:
        raise ValueError("No language has both labels in both source-disjoint splits")
    rng = random.Random(a.seed)

    @lru_cache(maxsize=256)
    def offsets(key):
        return tok(rows[key]["text"], add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]

    def excerpt(key, size, sentence_end=False):
        text = rows[key]["text"]
        off = offsets(key)
        if not off:
            return ""
        sents = split_sentences_with_offsets(text)
        start = rng.choice(sents).start if sents else 0
        part = text[start:]
        enc = tok(part, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        if not enc:
            return ""
        end = enc[min(size, len(enc)) - 1][1]
        if sentence_end:
            ends = [s.end for s in split_sentences_with_offsets(part) if s.end <= end and part[s.end - 1] in '.!?…\"\')»”']
            if not ends:
                return ""
            end = ends[-1]
        return part[:end].strip()

    def make(split, kind, lang):
        for _ in range(400):
            first_label = rng.choice(("ai", "human")) if kind == "mixed" else kind
            k1 = rng.choice(pools[split, lang, first_label])
            if kind == "mixed":
                k2 = rng.choice(pools[split, lang, "human" if first_label == "ai" else "ai"])
                left = excerpt(k1, rng.randint(max(1, round(.2 * budget)), round(.8 * budget)), True)
                if not left:
                    continue
                nl = len(tok(left, add_special_tokens=False)["input_ids"])
                right = excerpt(k2, budget - nl)
                text = left + "\n\n" + right
                enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
                if len(enc) > budget:
                    text = text[:enc[budget - 1][1]]
                    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
                before = sum(e <= len(left) for _, e in enc)
                if not right or len(text) <= len(left) + 2 or len(enc) > budget or not .2 <= before / len(enc) <= .8:
                    continue
                spans = [[0, len(left) + 2, int(first_label == "ai")],
                         [len(left) + 2, len(text), int(first_label != "ai")]]
                keys = [k1, k2]
            else:
                text = excerpt(k1, budget)
                if not text:
                    continue
                if len(tok(text, add_special_tokens=False)["input_ids"]) > budget:
                    continue
                spans, keys = [[0, len(text), int(first_label == "ai")]], [k1]
            return dict(text=text, spans=spans, lang=lang, split=split, kind=kind,
                        source_hashes=keys, source_h=[rows[k]["h"] for k in keys],
                        source_src=[rows[k]["src"] for k in keys], max_len=max_len)
        raise ValueError(f"Cannot construct {split}/{lang}/{kind} window with sentence boundary in 20-80%")

    # Exact global type counts, with a validation window first for --limit smoke runs.
    counts = [int(a.n * .4), int(a.n * .3)]
    kinds = ["mixed"] * counts[0] + ["human"] * counts[1] + ["ai"] * (a.n - sum(counts))
    rng.shuffle(kinds)
    nv = max(1, round(a.n * .1))
    val_indices = {i * a.n // nv for i in range(nv)}
    used = Counter()
    with a.out.open("x", encoding="utf-8") as f:
        for i, kind in enumerate(kinds):
            split = "val" if i in val_indices else "train"
            # Equal representation where possible; capacity prevents overusing tiny pools.
            lang = min(langs, key=lambda l: (used[split, l] / min(1000, min(len(pools[split, l, c]) for c in ("human", "ai"))), rng.random()))
            row = make(split, kind, lang)
            row["id"] = i
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            used[split, lang] += 1
    print(json.dumps(dict(windows=a.n, max_len=max_len, excluded=dict(stats),
                          available={f"{s}/{l}/{c}": len(v) for (s,l,c),v in pools.items()},
                          generated={f"{s}/{l}": n for (s,l),n in used.items()})), flush=True)


if __name__ == "__main__":
    main()
