# -*- coding: utf-8 -*-
"""Автообновление моделей при выходе релиза с новыми весами и очистка старого."""
from linda_desktop import app as app_mod, config, updater


def make_core(monkeypatch, update, started):
    monkeypatch.setattr(updater, "is_complete", lambda: True)
    core = app_mod.Core()
    core.manifest, core.manifest_raw, core.update = {"version": "1.4.0", "files": []}, b"{}", update
    monkeypatch.setattr(core.job, "start", lambda m, raw: started.append(m["version"]) or True)
    return core


def test_auto_download_once_per_version(repo, monkeypatch):
    started = []
    core = make_core(monkeypatch, {"weights_update": True, "app_required": False, "bytes_to_download": 1000}, started)
    core._maybe_auto_models(); core._maybe_auto_models()
    assert started == ["1.4.0"]  # один раз на версию: сбой не зацикливает загрузки


def test_no_auto_when_off_or_app_too_old_or_no_update(repo, monkeypatch):
    for up in ({"weights_update": False}, {"weights_update": True, "app_required": True}):
        started = []
        make_core(monkeypatch, up, started)._maybe_auto_models()
        assert started == []
    started = []
    core = make_core(monkeypatch, {"weights_update": True, "app_required": False}, started)
    from linda_desktop.engine import save_settings, load_settings
    save_settings({**load_settings(), "auto_models": False})
    core._maybe_auto_models()
    assert started == []


def test_no_auto_when_disk_is_full(repo, monkeypatch):
    from linda_desktop import models_location
    monkeypatch.setattr(models_location, "free_gb", lambda p: 0.5)
    started = []
    make_core(monkeypatch, {"weights_update": True, "app_required": False, "bytes_to_download": 3 * 2**30}, started)._maybe_auto_models()
    assert started == []


def test_prune_stale_onnx_and_empty_dirs(repo):
    root = config.data_dir()
    (root / "models" / "new_voice").mkdir(parents=True); (root / "models" / "new_voice" / "w.bin").write_bytes(b"1")
    (root / "models" / "empty_old").mkdir(parents=True)
    for d in ("new_voice", "old_voice"):
        (root / "onnx" / d).mkdir(parents=True); (root / "onnx" / d / "model.onnx").write_bytes(b"x")
    removed = updater.prune_stale(root)
    assert removed == ["onnx/old_voice"] and (root / "onnx" / "new_voice").is_dir() and not (root / "models" / "empty_old").exists()
