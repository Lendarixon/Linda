# -*- coding: utf-8 -*-
"""The ONNX/DirectML voter: windows, padding and scoring are identical to FastSeqCls (checked against a stub session, no GPU needed)."""
import json
import sys
import types
from pathlib import Path

import pytest
import numpy as np

from linda_desktop import onnx_gpu


class StubTok:
    cls_token_id, sep_token_id, pad_token_id = 1, 2, 0

    def __call__(self, texts, add_special_tokens=False):
        return {"input_ids": [[10 + (i % 50) for i, _ in enumerate(t.split())] for t in texts]}


class StubSession:
    """Returns logits whose difference equals the number of real tokens (so the mean over windows is checkable); records the batches."""

    def __init__(self, L):
        self.L, self.batches = L, []

    def run(self, names, feed):
        ids, mask = feed["input_ids"], feed["attention_mask"]
        assert ids.shape == mask.shape and ids.shape[1] == self.L and ids.dtype == np.int64  # fixed length, int64
        assert (ids[mask == 0] == 0).all() and (mask.sum(1) >= 2).all()  # padding hidden by the mask
        self.batches.append(len(ids))
        n = mask.sum(1).astype(np.float32)
        return [np.stack([np.zeros_like(n), n], axis=1)]


def make(tmp_path, max_len=32):
    o = onnx_gpu.OnnxSeqCls.__new__(onnx_gpu.OnnxSeqCls)
    o.max_len, o.tok, o.sess = max_len, StubTok(), StubSession(max_len)
    return o


def test_short_text_is_one_padded_window(tmp_path):
    o = make(tmp_path)
    z = o.margins(["one two three four five"])  # 5 tokens + CLS + SEP
    assert z == [7.0]


def test_long_text_is_split_in_windows_and_averaged(tmp_path):
    o = make(tmp_path)
    text = " ".join(["w"] * 100)  # 100 tokens; windows of max_len - 2 = 30 tokens
    z = o.margins([text])
    assert len(o._windows(list(range(100)))) == 4 and z == [32.0]  # four full windows of 30 + CLS + SEP
    assert max(o.sess.batches) <= onnx_gpu.MAX_BATCH


def test_batches_never_exceed_the_directml_limit(tmp_path):
    o = make(tmp_path)
    o.margins([" ".join(["w"] * 200)] * 5)  # 5 texts x 7 windows = 35 windows
    assert sum(o.sess.batches) == 35 and max(o.sess.batches) == onnx_gpu.MAX_BATCH


def test_each_text_gets_its_own_mean(tmp_path):
    o = make(tmp_path)
    z = o.margins(["a b c", " ".join(["w"] * 100)])
    assert z == [5.0, 32.0]


# --- Stable FP32 DirectML correctness (mocked construction, no inference) ---

def _fake_ort(monkeypatch, captured):
    ort = types.ModuleType("onnxruntime")
    transformers = types.ModuleType("transformers")
    seq = object()

    class Options:
        def __init__(self):
            self.config_entries = {}

        def add_session_config_entry(self, name, value):
            self.config_entries[name] = value

    class Session:
        def __init__(self, path, sess_options, providers):
            captured["sessions"].append((path, sess_options, providers))
            self.options, self.requested_providers = sess_options, providers

        def get_providers(self):
            return ["DmlExecutionProvider", "CPUExecutionProvider"]

        def run(self, *a, **k):
            raise AssertionError("mocked construction test must not run inference")

    class Tokenizer:
        @staticmethod
        def from_pretrained(path):
            captured["tokenizers"].append(path)
            return object()

    ort.SessionOptions = Options
    ort.ExecutionMode = types.SimpleNamespace(ORT_SEQUENTIAL=seq)
    ort.InferenceSession = Session
    transformers.AutoTokenizer = Tokenizer
    monkeypatch.setitem(sys.modules, "onnxruntime", ort)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    monkeypatch.setattr(onnx_gpu, "export", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not export")))
    return seq


def _disk(tmp_path, max_len=32, dtype="fp32", tokens=True, batch="static1"):
    model = tmp_path / "m"
    model.mkdir(exist_ok=True)
    (model / "train_args.json").write_text(json.dumps({"max_len": max_len}), encoding="utf-8")
    cache_root = tmp_path / "cache"
    for sub in ("m", "fp32_stable_v1/m", "fp32_stable_b1/m"):
        c = cache_root / sub
        c.mkdir(parents=True, exist_ok=True)
        (c / "model.onnx").write_bytes(b"fake")
        meta = {"max_len": max_len, "dtype": dtype}
        if sub.startswith("fp32_stable_b1"):
            meta["batch"] = batch
        (c / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
        if tokens:
            (c / "model_tok.onnx").write_bytes(b"fake")
            (c / "meta_tok.json").write_text(json.dumps(meta), encoding="utf-8")
    return model, cache_root


def test_stable_defaults_to_legacy(tmp_path):
    model, cache_root = _disk(tmp_path)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=1)
    assert o.stable is False and o.fp16 is False
    assert o.cache == cache_root / "m"


def test_legacy_fp16_still_allowed(tmp_path):
    model, cache_root = _disk(tmp_path, dtype="fp16")
    o = onnx_gpu.OnnxSeqCls(model, cache_root, fp16=True)
    assert o.stable is False and o.fp16 is True
    assert o.cache == cache_root / "m"


def test_stable_rejects_fp16(tmp_path):
    model, cache_root = _disk(tmp_path)
    with pytest.raises(ValueError):
        onnx_gpu.OnnxSeqCls(model, cache_root, fp16=True, stable=True)


def test_stable_cache_is_isolated(tmp_path):
    model, cache_root = _disk(tmp_path)
    s = onnx_gpu.OnnxSeqCls(model, cache_root, stable=True)
    legacy = onnx_gpu.OnnxSeqCls(model, cache_root)
    assert s.cache == cache_root / "fp32_stable_b1" / "m"
    assert s.cache != legacy.cache
    assert s.fp16 is False


def test_stable_freezes_the_batch_axis(tmp_path):
    """One window per run: a symbolic batch axis keeps DeBERTa's shape plumbing on the GPU (measured 1.7-3.2x)."""
    model, cache_root = _disk(tmp_path)
    assert onnx_gpu.OnnxSeqCls(model, cache_root, stable=True).static_batch is True
    assert onnx_gpu.OnnxSeqCls(model, cache_root, stable=True, max_batch=1).static_batch is True
    # A caller that really batches keeps the dynamic graph and the old namespace.
    b = onnx_gpu.OnnxSeqCls(model, cache_root, stable=True, max_batch=4)
    assert b.static_batch is False and b.cache == cache_root / "fp32_stable_v1" / "m"
    assert onnx_gpu.OnnxSeqCls(model, cache_root).static_batch is False


def test_export_freezes_batch_only_when_asked(tmp_path, monkeypatch):
    import types as _types
    captured = {}

    def fake_export(model, args, path, **kw):
        captured.update(kw)
        Path(path).write_bytes(b"graph")

    torch = _types.ModuleType("torch")
    torch.long = "int64"
    torch.ones = lambda shape, dtype=None: np.ones(shape, dtype=np.int64)
    torch.no_grad = __import__("contextlib").nullcontext
    torch.onnx = _types.SimpleNamespace(export=fake_export)
    class _M:
        def eval(self): return self
        def float(self): return self
        def half(self): return self
        def __call__(self, *a): return None
    transformers = _types.ModuleType("transformers")
    transformers.AutoModelForSequenceClassification = _types.SimpleNamespace(
        from_pretrained=lambda _p: _M())
    with monkeypatch.context() as m:
        m.setitem(sys.modules, "torch", torch)
        m.setitem(sys.modules, "transformers", transformers)
        onnx_gpu.export(tmp_path / "m", tmp_path / "o", 32, static_batch=True)
        assert "dynamic_axes" not in captured
        assert json.loads((tmp_path / "o" / "meta.json").read_text())["batch"] == "static1"
        onnx_gpu.export(tmp_path / "m", tmp_path / "o2", 32)
        assert captured["dynamic_axes"]["input_ids"] == {0: "batch"}
        assert json.loads((tmp_path / "o2" / "meta.json").read_text())["batch"] == "dynamic"


def test_stable_sets_deterministic_both_sessions(tmp_path, monkeypatch):
    model, cache_root = _disk(tmp_path)
    captured = {"sessions": [], "tokenizers": []}
    _fake_ort(monkeypatch, captured)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=2, stable=True)
    o._load()
    o._load_tokens()
    assert len(captured["sessions"]) == 2
    for path, so, providers in captured["sessions"]:
        assert getattr(so, "use_deterministic_compute", None) is True
        dml = dict(providers[0][1])
        assert providers[0][0] == "DmlExecutionProvider"
        assert dml.get("disable_metacommands") == "true"  # string, not bool
        assert dml.get("device_id") == 2
        assert "use_deterministic_compute" not in dml  # SessionOptions flag only
        assert providers[1] == "CPUExecutionProvider"
    assert str(captured["sessions"][0][0]).endswith("model.onnx")
    assert str(captured["sessions"][1][0]).endswith("model_tok.onnx")
    assert "fp32_stable_b1" in captured["sessions"][0][0]


def test_legacy_keeps_old_providers(tmp_path, monkeypatch):
    model, cache_root = _disk(tmp_path)
    captured = {"sessions": [], "tokenizers": []}
    _fake_ort(monkeypatch, captured)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=3)
    o._load()
    o._load_tokens()
    assert len(captured["sessions"]) == 2
    for _, so, providers in captured["sessions"]:
        assert getattr(so, "use_deterministic_compute", None) is None
        assert providers == [("DmlExecutionProvider", {"device_id": 3}), "CPUExecutionProvider"]
