# -*- coding: utf-8 -*-
"""GPU acceleration for any DirectX 12 graphics card on Windows (AMD Radeon, NVIDIA GeForce, Intel Arc) through ONNX Runtime + DirectML.

The installer ships the CPU build of PyTorch, so the transformer voters are exported once, on the user's own computer, from the downloaded weights to ONNX
(cached in the data folder) and then run through DirectML. Same windowing and scoring as `linda_pro.voters.FastSeqCls`.
Lessons from the earlier project that are built in: DeBERTa tracing bakes the relative-position bias for the dummy length, so the graph is exported for a FIXED
sequence length (every window is padded to it, the attention mask hides the padding); the inputs are passed in a fixed order; DirectML gets one window per run (see MAX_BATCH)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

MAX_BATCH = 1  # one window per run: measured 4-6x faster than batches of 2-8 on DirectML (RX 9070 XT), lighter on memory, scores within 0.1 of the torch reference


def available() -> bool:
    try:
        import onnxruntime as ort

        return "DmlExecutionProvider" in ort.get_available_providers()
    except Exception:  # noqa: BLE001
        return False


def export(model_dir: Path, out_dir: Path, max_len: int) -> Path:
    """Export model_dir (HF sequence classifier) to out_dir/model.onnx for sequences of exactly max_len tokens (batch is dynamic)."""
    import torch
    from transformers import AutoModelForSequenceClassification

    out_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval().float()
    ids = torch.ones((1, max_len), dtype=torch.long)
    ids[0, 0] = 1
    mask = torch.ones((1, max_len), dtype=torch.long)
    target = out_dir / "model.onnx"
    tmp = out_dir / "model.onnx.part"
    kw = dict(input_names=["input_ids", "attention_mask"], output_names=["logits"],
              dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    with torch.no_grad():
        try:
            torch.onnx.export(model, (ids, mask), str(tmp), dynamo=False, **kw)  # the TorchScript exporter is the reliable one for DeBERTa
        except TypeError:  # older torch without the dynamo switch
            torch.onnx.export(model, (ids, mask), str(tmp), **kw)
    tmp.replace(target)
    (out_dir / "meta.json").write_text(json.dumps({"max_len": max_len, "source": str(model_dir.name)}), encoding="utf-8")
    return target


class OnnxSeqCls:
    """Drop-in replacement of FastSeqCls (margins / close) that runs on the GPU through DirectML."""

    def __init__(self, model_dir: str | Path, cache_dir: str | Path, device_id: int = 0):
        self.model_dir = Path(model_dir)
        self.cache = Path(cache_dir) / self.model_dir.name
        self.device_id = device_id
        args = self.model_dir / "train_args.json"
        self.max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
        self.sess = None

    def _load(self) -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        onnx_path = self.cache / "model.onnx"
        meta = self.cache / "meta.json"
        ok = onnx_path.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8")).get("max_len") == self.max_len
        if not ok:
            export(self.model_dir, self.cache, self.max_len)
        self.tok = AutoTokenizer.from_pretrained(str(self.model_dir))
        so = ort.SessionOptions()
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=[("DmlExecutionProvider", {"device_id": self.device_id}), "CPUExecutionProvider"])

    def close(self) -> None:
        self.sess = None

    def _windows(self, ids: list[int]) -> list[list[int]]:
        n = self.max_len - 2
        if len(ids) <= n:
            return [ids]
        k = math.ceil(len(ids) / n)
        starts = np.linspace(0, len(ids) - n, k).round().astype(int)
        return [ids[s: s + n] for s in starts]

    def margins(self, texts: list[str]) -> list[float]:
        if self.sess is None:
            self._load()
        tok = self.tok
        all_ids = tok(texts, add_special_tokens=False)["input_ids"]
        wins, owner = [], []
        for i, ids in enumerate(all_ids):
            for w in self._windows(ids) or [[]]:
                wins.append([tok.cls_token_id, *w, tok.sep_token_id])
                owner.append(i)
        L, pad = self.max_len, tok.pad_token_id
        z = np.zeros(len(wins))
        for b in range(0, len(wins), MAX_BATCH):
            chunk = wins[b: b + MAX_BATCH]
            ids = np.full((len(chunk), L), pad, dtype=np.int64)
            mask = np.zeros((len(chunk), L), dtype=np.int64)
            for r, w in enumerate(chunk):
                ids[r, : len(w)] = w
                mask[r, : len(w)] = 1
            lg = self.sess.run(["logits"], {"input_ids": ids, "attention_mask": mask})[0].astype(np.float32)
            z[b: b + len(chunk)] = lg[:, 1] - lg[:, 0] if lg.shape[1] == 2 else lg[:, 0]
        out = np.zeros(len(texts))
        cnt = np.zeros(len(texts))
        np.add.at(out, owner, z)
        np.add.at(cnt, owner, 1)
        return (out / cnt).tolist()
