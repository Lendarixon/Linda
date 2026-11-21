# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

from linda_desktop import humanize_pack, packs


def _setup_env(monkeypatch, tmp_path):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(tmp_path / "models"))


def test_base_ready_requires_complete_weights(monkeypatch, tmp_path):
    _setup_env(monkeypatch, tmp_path)
    base = humanize_pack.variant_dirs("lite")["base"]
    base.mkdir(parents=True)
    # Only config.json (partial download) must NOT count as ready
    (base / "config.json").write_text("{}", encoding="utf-8")
    assert humanize_pack.base_ready("lite") is False

    # Sharded index with missing shard -> False
    (base / "model.safetensors.index.json").write_text(
        json.dumps({"weight_map": {"a": "s1.safetensors", "b": "s2.safetensors"}}),
        encoding="utf-8",
    )
    (base / "s1.safetensors").write_bytes(b"1234")
    assert humanize_pack.base_ready("lite") is False

    # All shards present -> True
    (base / "s2.safetensors").write_bytes(b"5678")
    assert humanize_pack.base_ready("lite") is True


def test_trace_res_finds_frozen_internal_adapter(monkeypatch, tmp_path):
    fake_exe = tmp_path / "app" / "Linda-Pro.exe"
    internal_trace = tmp_path / "app" / "_internal" / "linda_desktop" / "trace"
    internal_trace.mkdir(parents=True)
    (internal_trace / "humanizer_adapter_lite.safetensors").write_bytes(b"adapter")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "empty_meipass"), raising=False)
    assert humanize_pack._trace_res() == internal_trace


def test_download_base_idempotent_and_cleans_duplicates(monkeypatch, tmp_path):
    _setup_env(monkeypatch, tmp_path)
    d = humanize_pack.variant_dirs("lite")
    d["base"].mkdir(parents=True)
    (d["base"] / "config.json").write_text("{}", encoding="utf-8")
    (d["base"] / "model.safetensors").write_bytes(b"weights")
    d["adapter"].write_bytes(b"adapter")
    dl_cache = d["base"] / ".cache" / "huggingface" / "download"
    dl_cache.mkdir(parents=True)
    stale = dl_cache / "foo.incomplete"
    stale.write_bytes(b"junk")
    dup_dir = d["root"].parent / "humanizer-lite_copy"
    dup_dir.mkdir(parents=True)

    # Must not invoke huggingface_hub.snapshot_download when already installed
    called = []
    monkeypatch.setitem(sys.modules, "huggingface_hub", type("M", (), {"snapshot_download": lambda *a, **k: called.append(1)})())
    humanize_pack.download_base("lite")
    assert called == []
    assert d["ready"].is_file()
    assert not stale.exists()
    assert not dup_dir.exists()


def test_packs_probe_includes_job(monkeypatch, tmp_path):
    _setup_env(monkeypatch, tmp_path)
    st = packs.probe()
    assert "job" in st and "phase" in st["job"]


def test_desktop_shell_version_not_hardcoded():
    src = Path("web/desktop-shell.js").read_text(encoding="utf-8")
    assert "Linda 2.3.0.1" not in src
    assert "window.LINDA_BOOT" in src


def test_conftest_isolates_linda_env(tmp_path):
    import os
    from linda_desktop import config

    assert Path(os.environ["LINDA_HOME"]) == tmp_path / "_linda_home"
    assert "LINDA_MODELS_HOME" not in os.environ
    assert "LINDA_BASE_URL" not in os.environ
    assert config.data_dir() == tmp_path / "_linda_home"
    assert config.models_root() == tmp_path / "_linda_home"

