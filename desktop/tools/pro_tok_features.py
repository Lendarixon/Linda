"""Export frozen DeBERTa logits + last hidden state; extract real-token features.

Fixed sequence length, dynamic batch, positional (ids, mask), as onnx_gpu.py.
NPZ uses no pickle: flat hidden[N,1024], labels[N] (AI character overlap),
window_ptr[W+1], window_id/split/lang/offsets/sentence_id per token, plus
sentence_human_words/ai_words. Cache and scratch live under --cache-dir (temp).
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ[name] = "4"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from linda_desktop.sentences import split_sentences_with_offsets


def overlap_label(start, end, spans):
    total = sum(max(0, min(end, b) - max(start, a)) for a, b, _ in spans)
    ai = sum(max(0, min(end, b) - max(start, a)) * y for a, b, y in spans)
    if total != end - start or total <= 0:
        raise ValueError("Character label spans must cover each real token exactly once")
    return ai / total


def export(model_dir, cache, max_len):
    import torch
    from transformers import AutoModelForSequenceClassification
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    inputs = [p for p in model_dir.iterdir() if p.is_file() and p.suffix in (".json", ".safetensors", ".bin", ".model")]
    identity = dict(version=1, source=str(model_dir.resolve()), max_len=max_len,
                    files=[[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in sorted(inputs)])
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    folder = cache / fingerprint
    target = folder / "tokens.onnx"
    meta = folder / "meta.json"
    if target.exists() and meta.exists() and json.loads(meta.read_text()) == identity:
        return target
    folder.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Unverified cache file: {target}; use another --cache-dir")
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir), local_files_only=True).cpu().float().eval()
    if model.config.model_type != "deberta-v2":
        raise ValueError("Expected DeBERTa-v2")  # Essay large: 1024, Multi base: 768
    model.requires_grad_(False)

    class Wrapper(torch.nn.Module):
        def __init__(self, classifier):
            super().__init__()
            self.model = classifier

        def forward(self, input_ids, attention_mask):
            m = self.model
            h = m.deberta(input_ids=input_ids, attention_mask=attention_mask, return_dict=False)[0]
            logits = m.classifier(m.dropout(m.pooler(h)))
            return logits, h

    wrapper = Wrapper(model).eval()
    ids = torch.ones((1, max_len), dtype=torch.long)
    mask = torch.ones_like(ids)
    kwargs = dict(input_names=["input_ids", "attention_mask"],
                  output_names=["logits", "last_hidden_state"], opset_version=17,
                  dynamic_axes={n: {0: "batch"} for n in ("input_ids", "attention_mask", "logits", "last_hidden_state")})
    print(f"Exporting frozen CPU model, fixed length {max_len}", flush=True)
    # Explicit dynamo=False selects the tested TorchScript exporter. No sequence axis is dynamic.
    with torch.inference_mode():
        reference = model(ids, mask).logits
        actual, _ = wrapper(ids, mask)
        torch.testing.assert_close(actual, reference)
        import inspect
        if "dynamo" in inspect.signature(torch.onnx.export).parameters:
            kwargs["dynamo"] = False
        torch.onnx.export(wrapper, (ids, mask), str(target), **kwargs)
    with meta.open("x", encoding="utf-8") as f:
        json.dump(identity, f)
    del wrapper, model
    gc.collect()
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("data", type=Path)
    p.add_argument("model_dir", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--device", choices=("dml", "cpu"), default="cpu")
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--limit", type=int)
    p.add_argument("--cache-dir", type=Path, default=Path(tempfile.gettempdir()) / "linda_pro_tok_onnx")
    a = p.parse_args()
    if not 1 <= a.batch <= 4 or (a.limit is not None and a.limit < 1):
        p.error("batch must be 1..4 and limit positive")
    if a.out.exists():
        raise FileExistsError(a.out)
    import onnxruntime as ort
    from transformers import AutoTokenizer
    if a.device == "dml" and "DmlExecutionProvider" not in ort.get_available_providers():
        raise RuntimeError("DmlExecutionProvider unavailable; refusing silent CPU fallback")
    tok = AutoTokenizer.from_pretrained(str(a.model_dir), local_files_only=True, use_fast=True)
    if not tok.is_fast:
        raise ValueError("Fast tokenizer required")
    args = a.model_dir / "train_args.json"
    max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
    rows, encoded = [], []
    with a.data.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            if r["split"] not in ("train", "val") or r["lang"] not in ("en", "ru", "pl"):
                raise ValueError("Unknown split or language")
            # Explicit special tokens match the app; do not use implicit tokenizer templates.
            enc = tok(r["text"], add_special_tokens=False, return_offsets_mapping=True)
            if len(enc["input_ids"]) > max_len - 2:
                # окна нарезаны токенизатором Essay; у Multi токенов может быть больше - лишний хвост отбрасывается (метки идут по символам)
                enc = {k: v[: max_len - 2] for k, v in enc.items()}
            if not enc["input_ids"]:
                raise ValueError("Empty window")
            spans = r["spans"]
            end = 0
            for start, stop, label in spans:
                if start != end or stop <= start or label not in (0, 1):
                    raise ValueError("Invalid label spans")
                end = stop
            if end != len(r["text"]):
                raise ValueError("Spans do not cover text")
            rows.append(r)
            encoded.append(enc)
            if a.limit and len(rows) >= a.limit:
                break
    if not rows:
        raise ValueError("No data")
    # Defensive source split check, including user-supplied data.
    source_splits = {}
    for r in rows:
        for h in r.get("source_hashes", []):
            if h in source_splits and source_splits[h] != r["split"]:
                raise ValueError("Source text appears in both splits")
            source_splits[h] = r["split"]
    counts = [sum(e > s for s,e in enc["offset_mapping"]) for enc in encoded]
    ptr = np.r_[0, np.cumsum(counts)].astype(np.int64)
    graph = export(a.model_dir, a.cache_dir, max_len)
    HS = int(json.loads((Path(a.model_dir) / "config.json").read_text(encoding="utf-8"))["hidden_size"])  # Essay 1024, Multi 768
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    so.inter_op_num_threads = 1
    so.add_session_config_entry("session.intra_op.allow_spinning", "0")
    so.enable_mem_pattern = False
    so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    so.log_severity_level = 3
    providers = ["CPUExecutionProvider"] if a.device == "cpu" else [("DmlExecutionProvider", {"device_id": 0}), "CPUExecutionProvider"]
    session = ort.InferenceSession(str(graph), sess_options=so, providers=providers)
    if a.device == "dml" and "DmlExecutionProvider" not in session.get_providers():
        raise RuntimeError("DirectML session not active")
    if [v.name for v in session.get_inputs()] != ["input_ids", "attention_mask"]:
        raise ValueError("Unexpected ONNX positional input order")
    # Disk-backed hidden storage avoids accumulating multi-GB float32 states in RAM.
    scratch = Path(tempfile.mkdtemp(prefix="pro_tok_features_", dir=a.cache_dir))
    hidden = np.lib.format.open_memmap(scratch / "hidden.npy", mode="w+", dtype=np.float16, shape=(int(ptr[-1]), HS))
    labels, offsets, sentence_ids, human_words, ai_words, sentence_lang = [], [], [], [], [], []
    logits = []
    for b in range(0, len(rows), a.batch):
        chunk = rows[b:b+a.batch]
        ids = np.full((len(chunk), max_len), tok.pad_token_id, dtype=np.int64)
        mask = np.zeros_like(ids)
        for j in range(len(chunk)):
            real = encoded[b+j]["input_ids"]
            ids[j, :len(real)+2] = [tok.cls_token_id, *real, tok.sep_token_id]
            mask[j, :len(real)+2] = 1
        lg, states = session.run(["logits", "last_hidden_state"], {"input_ids": ids, "attention_mask": mask})
        if states.shape != (len(chunk), max_len, HS) or not np.isfinite(states).all():
            raise ValueError("Invalid hidden states")
        logits.extend(lg.tolist())
        for j, r in enumerate(chunk):
            off = encoded[b+j]["offset_mapping"]
            real_idx = [k for k,(s,e) in enumerate(off) if e > s]
            hidden[ptr[b+j]:ptr[b+j+1]] = states[j, np.array(real_idx)+1].astype(np.float16)
            sents = split_sentences_with_offsets(r["text"])
            base = len(human_words)
            for sent in sents:
                h = ai = 0
                for word in re.finditer(r"[^\W\d_]+", sent.text, re.UNICODE):
                    y = overlap_label(sent.start+word.start(), sent.start+word.end(), r["spans"]) >= .5
                    ai += int(y)
                    h += int(not y)
                human_words.append(h)
                ai_words.append(ai)
                sentence_lang.append(r["lang"])
            for k in real_idx:
                start, end = off[k]
                labels.append(overlap_label(start, end, r["spans"]))
                offsets.append((start, end))
                overlaps = [max(0, min(end,s.end)-max(start,s.start)) for s in sents]
                sentence_ids.append(base + int(np.argmax(overlaps)) if overlaps and max(overlaps) > 0 else -1)
        del states
        print(f"Features {min(b+a.batch,len(rows))}/{len(rows)}", flush=True)
        time.sleep(.05)
    hidden.flush()
    if not np.isfinite(hidden).all():
        raise ValueError("Hidden states overflowed fp16")
    metadata = json.dumps(dict(model_dir=str(a.model_dir.resolve()), graph=str(graph), max_len=max_len,
                               hidden_size=HS, label="AI char-overlap fraction", sentence_score="mean token logit"))
    with a.out.open("xb") as f:
        np.savez(f, hidden=hidden, labels=np.array(labels, np.float32), offsets=np.array(offsets,np.int32),
                 window_ptr=ptr, window_id=np.repeat(np.arange(len(rows)),counts),
                 split=np.repeat(np.array([r["split"] for r in rows]),counts),
                 lang=np.repeat(np.array([r["lang"] for r in rows]),counts),
                 sentence_id=np.array(sentence_ids,np.int32), sentence_human_words=np.array(human_words,np.int32),
                 sentence_ai_words=np.array(ai_words,np.int32), sentence_lang=np.array(sentence_lang),
                 ids=np.array([str(r.get("id",i)) for i,r in enumerate(rows)]),
                 logits=np.array(logits,np.float32), metadata=np.array(metadata))
    print(f"Saved {a.out}: {len(labels)} tokens, hidden fp16; scratch retained at {scratch}")


if __name__ == "__main__":
    main()
