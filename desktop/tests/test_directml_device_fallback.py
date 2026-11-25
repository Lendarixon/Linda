# -*- coding: utf-8 -*-
"""DirectML cp1251 error decoding, adapter fallback, OOM/TDR recovery, VRAM budget, and token eviction."""
import json
import sys
import types

import pytest

from linda_desktop import engine, onnx_gpu
from linda_pro.routed import ModelPool


def _make_cp1251_decode_err(text: str) -> UnicodeDecodeError:
    raw = text.encode("cp1251")
    return UnicodeDecodeError("utf-8", raw, 0, 1, "invalid continuation byte")


def test_decode_ort_error_cp1251_bytes():
    err = _make_cp1251_decode_err("8007000E Недостаточно ресурсов памяти")
    out = onnx_gpu.decode_ort_error(err)
    assert "8007000E" in out
    assert "Недостаточно ресурсов памяти" in out


def test_default_vram_budget_scales_with_gpu_memory(monkeypatch):
    monkeypatch.setattr(engine, "_adapters", lambda: [{"name": "GTX 1650 SUPER", "vram": 4 * 1024**3, "discrete": True}])
    assert engine._default_vram_budget_mb("dml", 0) == 2000

    monkeypatch.setattr(engine, "_adapters", lambda: [{"name": "RTX 5060", "vram": 8 * 1024**3, "discrete": True}])
    assert engine._default_vram_budget_mb("dml", 0) == 3200

    monkeypatch.setattr(engine, "_adapters", lambda: [{"name": "RX 9070 XT", "vram": 16 * 1024**3, "discrete": True}])
    assert engine._default_vram_budget_mb("dml", 0) == 5200

    assert engine._default_vram_budget_mb("cpu", 0) == 9000


def test_model_pool_evict_for_tokens_frees_other_voters():
    closed = []

    class DummyVoter:
        def __init__(self, name, has_tok=False):
            self.name = name
            self.tok_sess = object() if has_tok else None

        def close(self):
            closed.append(self.name)

    pool = ModelPool(lambda k: DummyVoter(k), {"essay": 1740, "multi": 1120}, budget_mb=3200)
    pool.get("essay_m")
    pool.get("multi_m")
    assert set(pool.items) == {"essay_m", "multi_m"}
    pool.evict_for_tokens("essay_m")
    assert "multi_m" in closed
    assert list(pool.items) == ["essay_m"]


def _setup_ort_disk(tmp_path, monkeypatch, factory):
    model = tmp_path / "m"
    model.mkdir()
    (model / "train_args.json").write_text(json.dumps({"max_len": 32}), encoding="utf-8")
    cache = tmp_path / "cache" / "fp32_stable_b1" / "m"
    cache.mkdir(parents=True)
    (cache / "model.onnx").write_bytes(b"fake")
    (cache / "meta.json").write_text(json.dumps({"max_len": 32, "dtype": "fp32", "batch": "static1"}), encoding="utf-8")
    (cache / "model_tok.onnx").write_bytes(b"fake")
    (cache / "meta_tok.json").write_text(json.dumps({"max_len": 32, "dtype": "fp32", "batch": "static1"}), encoding="utf-8")

    ort = types.ModuleType("onnxruntime")
    transformers = types.ModuleType("transformers")

    class Options:
        def add_session_config_entry(self, k, v):
            pass

    ort.SessionOptions = Options
    ort.ExecutionMode = types.SimpleNamespace(ORT_SEQUENTIAL=object())
    ort.InferenceSession = factory
    transformers.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda _p: object())
    monkeypatch.setitem(sys.modules, "onnxruntime", ort)
    monkeypatch.setitem(sys.modules, "transformers", transformers)
    return model, tmp_path / "cache"


def test_dml_probes_next_device_on_887a0002(tmp_path, monkeypatch):
    calls = []

    class Session:
        def __init__(self, path, sess_options, providers):
            did = providers[0][1]["device_id"]
            calls.append(did)
            if did == 2:
                raise _make_cp1251_decode_err("887A0002 Объект не найден. IDXGIFactory::EnumAdaptes")

        def get_providers(self):
            return ["DmlExecutionProvider", "CPUExecutionProvider"]

    model, cache_root = _setup_ort_disk(tmp_path, monkeypatch, Session)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=2, stable=True)
    o._load()
    assert o.device_id == 0
    assert calls == [2, 0]


def test_dml_tdr_retries_without_disable_metacommands(tmp_path, monkeypatch):
    attempts = []

    class Session:
        def __init__(self, path, sess_options, providers):
            dm = providers[0][1].get("disable_metacommands")
            attempts.append(dm)
            if dm == "true":
                raise _make_cp1251_decode_err("887A0006 Графический процессор не будет отвечать")

        def get_providers(self):
            return ["DmlExecutionProvider", "CPUExecutionProvider"]

    model, cache_root = _setup_ort_disk(tmp_path, monkeypatch, Session)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=0, stable=True)
    o._load()
    assert attempts == ["true", None]


def test_dml_releases_main_session_before_loading_tokens(tmp_path, monkeypatch):
    class Session:
        def __init__(self, path, sess_options, providers):
            self.path = path

        def get_providers(self):
            return ["DmlExecutionProvider", "CPUExecutionProvider"]

    model, cache_root = _setup_ort_disk(tmp_path, monkeypatch, Session)
    o = onnx_gpu.OnnxSeqCls(model, cache_root, device_id=0, stable=True)
    o.release_main_for_tokens = True
    o._load()
    assert o.sess is not None
    o._load_tokens()
    assert o.sess is None
    assert o.tok_sess is not None
