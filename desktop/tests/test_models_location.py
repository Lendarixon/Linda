# -*- coding: utf-8 -*-
"""Папка для моделей: указатель, проверка, перенос с прогрессом, API."""
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, config, models_location, updater


def test_default_then_custom_pointer(repo, tmp_path):
    assert config.models_root() == config.data_dir()
    target = tmp_path / "models-here"
    config.set_models_root(target)
    assert config.models_root() == target and config.models_location_state()["custom"]
    config.set_models_root(None)
    assert config.models_root() == config.data_dir()


def test_unreachable_folder_falls_back_and_reports(repo, tmp_path, monkeypatch):
    (config.data_dir() / "models_location.json").write_text(json.dumps({"path": str(tmp_path / "x" / "y")}), encoding="utf-8")
    real_mkdir = Path.mkdir

    def failing(self, *a, **k):
        if "x" in self.parts and self.name in ("x", "y"):
            raise OSError("drive missing")
        return real_mkdir(self, *a, **k)

    monkeypatch.setattr(Path, "mkdir", failing)
    st = config.models_location_state()
    assert st["ok"] is False and config.models_root() == config.data_dir()


def test_validate(tmp_path):
    assert models_location.validate("relative/dir") == (False, "loc_bad")
    assert models_location.validate("\\server\share\m") == (False, "loc_bad")
    ok, key = models_location.validate(str(tmp_path / "ok"))
    assert ok, key


def test_move_job_copies_then_switches(repo, tmp_path):
    root = config.data_dir()
    (root / "models" / "m1").mkdir(parents=True)
    (root / "models" / "m1" / "w.bin").write_bytes(b"x" * 5000)
    (root / "manifest.json").write_text("{}", encoding="utf-8")
    new = tmp_path / "moved"
    job = models_location.MoveJob()
    job.start(root, new)
    for _ in range(100):
        if job.state["phase"] in ("done", "error"):
            break
        time.sleep(0.05)
    assert job.state["phase"] == "done", job.state
    assert (new / "models" / "m1" / "w.bin").read_bytes() == b"x" * 5000 and (new / "manifest.json").exists()
    assert not (root / "models").exists() and config.models_root() == new  # старая копия убрана, указатель переключён
    assert job.state["done"] == job.state["total"] == 5002


def test_api_location_and_status(repo, tmp_path, monkeypatch):
    monkeypatch.setattr(updater, "is_complete", lambda: True)
    core = app_mod.Core()
    with TestClient(app_mod.create_app(core, token="t")) as c:
        c.headers["x-linda-token"] = "t"
        st = c.get("/api/status").json()
        assert st["models_location"]["custom"] is False and st["models_move"]["phase"] == "idle"
        bad = c.post("/api/models/location", json={"path": "relative"})
        assert bad.status_code == 400
        good = c.post("/api/models/location", json={"path": str(tmp_path / "newroot")})
        assert good.status_code == 200 and good.json()["custom"] is True
        assert Path(c.get("/api/models/location").json()["path"]) == tmp_path / "newroot"
        back = c.post("/api/models/location", json={"path": ""})
        assert back.status_code == 200 and c.get("/api/models/location").json()["custom"] is False
