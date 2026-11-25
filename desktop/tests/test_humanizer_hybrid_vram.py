# -*- coding: utf-8 -*-
"""Universal VRAM unload, CUDA cache release, and hybrid GPU+CPU offload for Humanizer-Full 4B."""
import sys
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from linda_desktop import engine as eng_mod, humanize_pack, licensing
from linda_desktop.app import Core, create_app


def test_engine_unload_calls_cuda_empty_cache(monkeypatch):
    called = []
    fake_torch = types.ModuleType("torch")
    fake_torch.cuda = types.SimpleNamespace(
        is_available=lambda: True,
        empty_cache=lambda: called.append("empty_cache"),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setattr(eng_mod, "pick_device", lambda _p="auto": "cpu")
    monkeypatch.setattr(eng_mod, "load_settings", lambda: {"device": "auto"})

    e = eng_mod.Engine()
    e.unload()
    assert called == ["empty_cache"]


def test_humanize_endpoint_unloads_detector_before_loading_humanizer(monkeypatch):
    events = []
    core = Core()
    monkeypatch.setattr(core.engine, "unload", lambda: events.append("engine_unload"))
    monkeypatch.setattr(licensing, "check_licensed", lambda *_a, **_k: None)

    def fake_humanize(text, spans=None, mode="all", variant="auto", progress=None):
        events.append("humanize")
        return {
            "text": text,
            "changes": [],
            "changed": 0,
            "variant": "full",
            "placement": "hybrid (5.3 GB GPU + CPU)",
            "resolve": {"requested": variant, "used": "full", "plan": {}},
            "input_words": 5,
            "output_words": 5,
        }

    monkeypatch.setattr(humanize_pack, "humanize", fake_humanize)
    monkeypatch.setattr(humanize_pack, "unload", lambda: events.append("hum_unload"))

    app = create_app(core, token="t")
    client = TestClient(app)
    r = client.post(
        "/api/humanize",
        headers={"X-Linda-Token": "t"},
        json={"text": "Один два три четыре пять", "mode": "all", "variant": "full"},
    )
    assert r.status_code == 200
    assert events[:2] == ["engine_unload", "humanize"]
    assert "hum_unload" in events


def _patch_load_stack(monkeypatch, tmp_path, free_vram_gb: float, free_ram_gb: float):
    d = tmp_path / "full"
    base = d / "base"
    base.mkdir(parents=True)
    adapter = d / "adapter_model.safetensors"
    adapter.write_bytes(b"a")

    monkeypatch.setattr(humanize_pack, "ensure_runtime", lambda: tmp_path)
    monkeypatch.setattr(humanize_pack, "variant_dirs", lambda _v: {"root": d, "base": base, "adapter": adapter, "adapter_cfg": d / "cfg.json", "ready": d / "READY"})
    monkeypatch.setattr(humanize_pack, "_link_bundled_adapter", lambda _v: None)
    monkeypatch.setattr(humanize_pack, "base_ready", lambda _v: True)
    monkeypatch.setattr(humanize_pack, "free_ram_gb", lambda: free_ram_gb)

    fake_torch = types.ModuleType("torch")
    fake_torch.bfloat16 = "bf16"
    fake_torch.float16 = "fp16"
    fake_torch.float32 = "fp32"
    fake_torch.cuda = types.SimpleNamespace(
        is_available=lambda: True,
        empty_cache=lambda: None,
        mem_get_info=lambda: (int(free_vram_gb * 1024**3), int(8.0 * 1024**3)),
    )
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    class _FakeModel:
        def __init__(self):
            self.to_calls = []

        def merge_and_unload(self):
            return self

        def eval(self):
            return self

        def to(self, dev):
            self.to_calls.append(dev)
            return self

    class _FakeTok:
        pad_token = None
        eos_token = "<eos>"
        padding_side = "right"

    fake_tf = types.ModuleType("transformers")
    fake_tf.AutoTokenizer = types.SimpleNamespace(from_pretrained=lambda *_a, **_k: _FakeTok())
    fake_tf.AutoModelForCausalLM = types.SimpleNamespace(from_pretrained=lambda *_a, **_k: _FakeModel())
    monkeypatch.setitem(sys.modules, "transformers", fake_tf)

    fake_peft = types.ModuleType("peft")
    fake_peft.PeftModel = types.SimpleNamespace(from_pretrained=lambda m, _p: m)
    monkeypatch.setitem(sys.modules, "peft", fake_peft)


def test_load_full_pure_cuda_when_vram_ge_9gb(monkeypatch, tmp_path):
    _patch_load_stack(monkeypatch, tmp_path, free_vram_gb=10.5, free_ram_gb=12.0)
    b = humanize_pack.HumanizerBackend()
    assert b.load("full") == "full"
    assert b.placement == "cuda"
    assert b.batch_chunks == 4
    assert b.model.to_calls == ["cuda"]


def test_load_full_uses_hybrid_offload_on_8gb_rtx_5060(monkeypatch, tmp_path):
    _patch_load_stack(monkeypatch, tmp_path, free_vram_gb=6.5, free_ram_gb=6.0)
    seen = {}

    def fake_dispatch(model, fv, fr, dt):
        seen["args"] = (fv, fr, dt)
        model.hf_device_map = {"model.embed_tokens": 0, "model.layers.30": "cpu"}
        return model, "hybrid (5.3 GB GPU + CPU)"

    monkeypatch.setattr(humanize_pack, "_dispatch_hybrid", fake_dispatch)
    b = humanize_pack.HumanizerBackend()
    assert b.load("full") == "full"
    assert "hybrid" in b.placement
    assert b.batch_chunks == 1
    assert b.model.to_calls == []
    assert seen["args"][0] == pytest.approx(6.5, abs=0.05)


def test_load_full_rejects_when_vram_below_hybrid_min(monkeypatch, tmp_path):
    _patch_load_stack(monkeypatch, tmp_path, free_vram_gb=2.0, free_ram_gb=12.0)
    b = humanize_pack.HumanizerBackend()
    with pytest.raises(RuntimeError, match="humanizer-out-of-memory"):
        b.load("full")
