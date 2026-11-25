# -*- coding: utf-8 -*-
"""Humanizer Full 4B CUDA runtime installer, 7.5 GB threshold, and honest fallback reporting."""
import io
import json
import zipfile

import pytest

from linda_desktop import config, humanize_pack


def test_full_mem_threshold_allows_8gb_rtx_5060():
    assert humanize_pack.FULL_MEM_GB == 7.5


def test_ensure_cuda_runtime_selects_newest_cu128_wheel_and_extracts(tmp_path, monkeypatch):
    monkeypatch.setattr(__import__("sys"), "path", list(__import__("sys").path))
    monkeypatch.setattr(config, "models_root", lambda: tmp_path)
    maj, min_v = __import__("sys").version_info[:2]
    tag = f"cp{maj}{min_v}-cp{maj}{min_v}-win_amd64.whl"

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("torch/__init__.py", "__version__ = '2.9.1+cu128'\n")
    whl_bytes = buf.getvalue()

    index_html = (
        f'<a href="torch-2.8.0%2Bcu128-{tag}#sha256=1">2.8.0</a>'
        f'<a href="torch-2.9.1%2Bcu128-{tag}#sha256=2">2.9.1</a>'
    )

    class _Resp:
        def __init__(self, text="", content=b""):
            self.text = text
            self._content = content
            self.headers = {"content-length": str(len(content))}

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size=1024):
            yield self._content

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    seen_urls = []

    def fake_get(url, stream=False, timeout=30):
        seen_urls.append(url)
        if url.endswith(".whl"):
            return _Resp(content=whl_bytes)
        return _Resp(text=index_html)

    import requests
    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setenv("LINDA_TORCH_CU128_INDEX", "https://example.test/cu128/torch/")

    lib = humanize_pack.ensure_cuda_runtime()
    assert seen_urls[1].endswith(f"torch-2.9.1%2Bcu128-{tag}")
    assert (lib / "torch" / "__init__.py").is_file()
    ready = json.loads((lib / "READY.json").read_text(encoding="utf-8"))
    assert ready["cuda"] == "cu128"
    assert humanize_pack.cuda_runtime_ready() is True


def test_ensure_does_not_swallow_cuda_restart_error(monkeypatch):
    monkeypatch.setattr(humanize_pack, "device_plan", lambda _v: {"tier": "full", "ok": True, "note": ""})
    monkeypatch.setattr(humanize_pack, "installed", lambda _t: True)

    class _FakeBackend:
        variant = None

        def load(self, tier):
            raise RuntimeError("humanizer-cuda-restart: restart required")

    monkeypatch.setattr(humanize_pack, "_backend", _FakeBackend())
    with pytest.raises(RuntimeError, match="humanizer-cuda-restart"):
        humanize_pack.ensure("full")
