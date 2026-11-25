# -*- coding: utf-8 -*-
"""2.5.0.1 reinstall-reuse regression tests (installer + updater)."""
from __future__ import annotations

import json
from pathlib import Path

from linda_desktop import config, updater

ROOT = Path(__file__).resolve().parents[1]
ISS = ROOT / "installer" / "linda.iss"


def _setup_dirs(monkeypatch, tmp_path):
    home = tmp_path / "home"
    models = tmp_path / "models"
    monkeypatch.setenv("LINDA_HOME", str(home))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(models))
    home.mkdir(parents=True, exist_ok=True)
    models.mkdir(parents=True, exist_ok=True)
    return home, models


def _write_manifest(models: Path, version: str, files: list[dict] | None = None):
    m = {"schema": 1, "version": version, "files": files or []}
    (models / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return m


def test_iss_detects_saved_manifest_and_writes_reuse_models():
    s = ISS.read_text(encoding="utf-8")
    assert "function FindSavedModels(" in s
    assert "function DetectSavedModels(" in s
    assert "SavedModelsDir" in s
    assert "Linda-Pro*" in s
    assert "Packages" in s and "LocalState" in s
    assert "CompareVersionStr" in s
    for lang in ("english", "russian", "polish"):
        assert f"{lang}.ReuseFound=" in s
    assert "SetsReuseNote" in s
    assert "SetsPage.SelectedValueIndex" in s
    assert '"reuse_models":' in s


def test_selected_sets_honors_reuse_when_versions_match(monkeypatch, tmp_path):
    home, models = _setup_dirs(monkeypatch, tmp_path)
    _write_manifest(models, "1.5.0-nightly")
    (home / "installer_choice.json").write_text(
        json.dumps({
            "model_sets": ["pro"],
            "reuse_models": True,
            "reuse_version": "1.5.0-nightly",
            "reuse_sets": ["lite"],
        }),
        encoding="utf-8",
    )
    assert updater.selected_sets() == ["lite"]


def test_selected_sets_honors_dict_reuse_models_when_versions_match(monkeypatch, tmp_path):
    home, models = _setup_dirs(monkeypatch, tmp_path)
    _write_manifest(models, "2.5.0.1")
    (home / "installer_choice.json").write_text(
        json.dumps({
            "model_sets": ["pro"],
            "reuse_models": {"version": "2.5.0.1", "sets": ["pro", "lite"]},
        }),
        encoding="utf-8",
    )
    assert updater.selected_sets() == ["pro", "lite"]


def test_selected_sets_ignores_reuse_when_versions_differ(monkeypatch, tmp_path):
    home, models = _setup_dirs(monkeypatch, tmp_path)
    _write_manifest(models, "1.4.0")
    (home / "installer_choice.json").write_text(
        json.dumps({
            "model_sets": ["pro"],
            "reuse_models": True,
            "reuse_version": "1.5.0-nightly",
            "reuse_sets": ["lite"],
        }),
        encoding="utf-8",
    )
    assert updater.selected_sets() == ["pro"]


def test_selected_sets_settings_still_override_installer_reuse(monkeypatch, tmp_path):
    home, models = _setup_dirs(monkeypatch, tmp_path)
    _write_manifest(models, "1.5.0-nightly")
    (home / "settings.json").write_text(json.dumps({"model_sets": ["pro", "lite"]}), encoding="utf-8")
    (home / "installer_choice.json").write_text(
        json.dumps({
            "model_sets": ["lite"],
            "reuse_models": True,
            "reuse_version": "1.5.0-nightly",
            "reuse_sets": ["lite"],
        }),
        encoding="utf-8",
    )
    assert updater.selected_sets() == ["pro", "lite"]


def test_reuse_avoids_redownload_when_files_exist(monkeypatch, tmp_path):
    home, models = _setup_dirs(monkeypatch, tmp_path)
    files = [
        {"path": "models/linda_speed_00/w.bin", "size": 128, "sha256": "a" * 64, "set": "lite"},
        {"path": "models/essay_dhi_00/w.bin", "size": 256, "sha256": "b" * 64, "set": "pro"},
        {"path": "calibration/c.json", "size": 32, "sha256": "c" * 64, "set": "shared"},
    ]
    m = _write_manifest(models, "1.5.0-nightly", files)
    for f in files:
        if f["set"] in ("lite", "shared"):
            p = models / f["path"]
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"\0" * f["size"])
    (home / "installer_choice.json").write_text(
        json.dumps({
            "model_sets": ["lite"],
            "reuse_models": True,
            "reuse_version": "1.5.0-nightly",
            "reuse_sets": ["lite"],
        }),
        encoding="utf-8",
    )
    eff = updater.effective(m)
    assert updater.files_to_fetch(eff, models) == []
    assert updater.is_complete(eff, models) is True
    st = updater.update_status(eff)
    assert st["weights_update"] is False
    assert st["weights_missing"] is False
