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


def export(model_dir: Path, out_dir: Path, max_len: int, fp16: bool = False, tokens: bool = False) -> Path:
    """Export model_dir (HF sequence classifier) to out_dir/model.onnx for sequences of exactly max_len tokens (batch is dynamic).
    fp16=True halves the weights (Essay ~0.87 GB instead of 1.7 GB): the 2.0 voters have to fit a 4 GB card; the inputs stay int64, the logits are cast to float32 on read."""
    import torch
    from transformers import AutoModelForSequenceClassification

    out_dir.mkdir(parents=True, exist_ok=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval()
    model = model.half() if fp16 else model.float()
    if tokens:
        class TokenGraph(torch.nn.Module):
            def __init__(self, classifier):
                super().__init__()
                self.model = classifier

            def forward(self, input_ids, attention_mask):
                m = self.model
                h = m.base_model(input_ids=input_ids, attention_mask=attention_mask, return_dict=False)[0]
                return m.classifier(m.dropout(m.pooler(h))), h

        model = TokenGraph(model).eval()
    ids = torch.ones((1, max_len), dtype=torch.long)
    ids[0, 0] = 1
    mask = torch.ones((1, max_len), dtype=torch.long)
    target = out_dir / ("model_tok.onnx" if tokens else "model.onnx")
    tmp = target.with_suffix(".onnx.part")
    kw = dict(input_names=["input_ids", "attention_mask"], output_names=["logits"],
              dynamic_axes={"input_ids": {0: "batch"}, "attention_mask": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    if tokens:
        kw["output_names"].append("last_hidden_state")
        kw["dynamic_axes"]["last_hidden_state"] = {0: "batch"}
    with torch.no_grad():
        try:
            torch.onnx.export(model, (ids, mask), str(tmp), dynamo=False, **kw)  # the TorchScript exporter is the reliable one for DeBERTa
        except TypeError:  # older torch without the dynamo switch
            torch.onnx.export(model, (ids, mask), str(tmp), **kw)
    tmp.replace(target)
    (out_dir / ("meta_tok.json" if tokens else "meta.json")).write_text(json.dumps({"max_len": max_len, "source": str(model_dir.name), "dtype": "fp16" if fp16 else "fp32"}), encoding="utf-8")
    return target


class OnnxSeqCls:
    """Drop-in replacement of FastSeqCls (margins / close) that runs on the GPU through DirectML."""

    def __init__(self, model_dir: str | Path, cache_dir: str | Path, device_id: int = 0, fp16: bool = False,
                 max_batch: int | None = None, allow_export: bool = True):
        self.fp16 = fp16
        self.max_batch = None if max_batch is None else max(1, int(max_batch))
        self.allow_export = bool(allow_export)
        self.model_dir = Path(model_dir)
        self.cache = Path(cache_dir) / self.model_dir.name
        self.device_id = device_id
        args = self.model_dir / "train_args.json"
        self.max_len = int(json.loads(args.read_text(encoding="utf-8")).get("max_len", 256)) if args.exists() else 256
        self.sess = None
        self.tok_sess = None

    def _load(self) -> None:
        import onnxruntime as ort
        from transformers import AutoTokenizer

        onnx_path = self.cache / "model.onnx"
        meta = self.cache / "meta.json"
        m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        ok = onnx_path.exists() and m.get("max_len") == self.max_len and m.get("dtype", "fp32") == ("fp16" if self.fp16 else "fp32")
        if not ok:
            if not self.allow_export:
                raise RuntimeError('Prebuilt ONNX graph or matching metadata is missing; runtime export is disabled')
            export(self.model_dir, self.cache, self.max_len, fp16=self.fp16)
        self.tok = AutoTokenizer.from_pretrained(str(self.model_dir))
        so = ort.SessionOptions()
        so.intra_op_num_threads = 4
        so.inter_op_num_threads = 1
        so.add_session_config_entry('session.intra_op.allow_spinning','0')
        so.enable_mem_pattern = False
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(onnx_path), sess_options=so, providers=[("DmlExecutionProvider", {"device_id": self.device_id}), "CPUExecutionProvider"])
        if 'DmlExecutionProvider' not in self.sess.get_providers():
            self.sess = None
            raise RuntimeError('DirectML session is unavailable; GPU inference was not started')

    def close(self) -> None:
        self.sess = None
        self.tok_sess = None

    @property
    def has_token_scores(self):
        return (self.model_dir / "tok_head.npz").is_file()

    def _load_tokens(self):
        import onnxruntime as ort
        from transformers import AutoTokenizer

        path = self.cache / "model_tok.onnx"
        meta = self.cache / "meta_tok.json"
        m = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        if not (path.exists() and m.get("max_len") == self.max_len
                and m.get("dtype") == ("fp16" if self.fp16 else "fp32")):
            if not self.allow_export:
                raise RuntimeError("Token ONNX graph missing; runtime export is disabled")
            export(self.model_dir, self.cache, self.max_len, fp16=self.fp16, tokens=True)
        if not hasattr(self, "tok"):
            self.tok = AutoTokenizer.from_pretrained(str(self.model_dir))
        so = ort.SessionOptions()
        so.intra_op_num_threads, so.inter_op_num_threads = 4, 1
        so.add_session_config_entry("session.intra_op.allow_spinning", "0")
        so.enable_mem_pattern = False
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.log_severity_level = 3
        sess = ort.InferenceSession(str(path), sess_options=so,
            providers=[("DmlExecutionProvider", {"device_id": self.device_id}), "CPUExecutionProvider"])
        if "DmlExecutionProvider" not in sess.get_providers():
            raise RuntimeError("DirectML token session is unavailable")
        self.tok_sess = sess

    def token_scores(self, text):
        from linda_pro.voters import pro_token_scores
        if not self.has_token_scores:
            raise ValueError("Missing tok_head.npz")
        if self.tok_sess is None:
            self._load_tokens()

        def hidden(seq):
            ids = np.full((1, self.max_len), self.tok.pad_token_id, dtype=np.int64)
            mask = np.zeros_like(ids)
            ids[0, :len(seq)], mask[0, :len(seq)] = seq, 1
            return self.tok_sess.run(["last_hidden_state"], {"input_ids": ids, "attention_mask": mask})[0][0]

        return pro_token_scores(self, text, hidden)

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
        from linda_pro.voters import check_cancel

        instance_batch = getattr(self, 'max_batch', None)
        batch = instance_batch if instance_batch is not None else MAX_BATCH
        for b in range(0, len(wins), batch):
            check_cancel()
            chunk = wins[b: b + batch]
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
