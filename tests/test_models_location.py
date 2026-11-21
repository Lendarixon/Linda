# -*- coding: utf-8 -*-
"""Папка для моделей: указатель, проверка, перенос с прогрессом, API."""
import json
import time
from pathlib import Path

import pytest

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


def test_validate(repo, tmp_path):
    assert models_location.validate("relative/dir") == (False, "loc_bad")
    assert models_location.validate(r"\\server\share\m") == (False, "loc_bad")
    ok, key = models_location.validate(str(tmp_path / "ok"))
    assert ok, key


def test_validate_rejects_overlapping_roots_before_writing(repo, tmp_path):
    old = tmp_path / "old"
    config.set_models_root(old)
    inside = old / "models" / "inside"

    assert models_location.validate(str(inside)) == (False, "loc_overlap")
    assert models_location.validate(str(tmp_path)) == (False, "loc_overlap")
    assert models_location.validate(str(old)) == (False, "loc_overlap")
    assert not inside.exists()


@pytest.mark.parametrize("destination", ["nested", "ancestor", "same"])
def test_move_rejects_overlapping_resolved_roots_without_touching_files(repo, tmp_path, destination):
    old = tmp_path / "old"
    model = old / "models" / "weights.bin"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"model-data")
    marker = old / "models" / "preexisting.part"
    marker.write_bytes(b"keep-me")
    if destination == "nested":
        new = old / "models" / "inside"
    elif destination == "ancestor":
        new = tmp_path
    else:
        new = old
    if destination == "nested":
        new.mkdir(parents=True)
        (new / "unrelated.part").write_bytes(b"keep-this-too")

    config.set_models_root(old)
    before_called = []
    job = models_location.MoveJob()
    job._run(old, new, lambda: before_called.append(True))

    assert job.state["phase"] == "error" and "loc_overlap" in job.state["error"]
    assert not before_called
    assert config.models_root() == old
    assert model.read_bytes() == b"model-data"
    assert marker.read_bytes() == b"keep-me"
    if destination == "nested":
        assert (new / "unrelated.part").read_bytes() == b"keep-this-too"


def test_move_resolves_junction_alias_before_unload(repo, tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    alias = tmp_path / "old-alias"
    try:
        alias.symlink_to(old, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip("directory symlink creation is unavailable: %s" % exc)
    assert models_location._roots_overlap(old, alias)

    before_called = []
    job = models_location.MoveJob()
    job._run(old, alias, lambda: before_called.append(True))
    assert job.state["phase"] == "error" and not before_called


def test_failed_move_cleanup_keeps_unowned_part_files(repo, tmp_path, monkeypatch):
    old = tmp_path / "old"
    source = old / "models" / "weights.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"model-data")
    new = tmp_path / "new"
    new.mkdir()
    unrelated = new / "unrelated.part"
    unrelated.write_bytes(b"not-owned")
    config.set_models_root(old)

    def fail_switch(_path):
        raise OSError("synthetic pointer failure")

    monkeypatch.setattr(config, "set_models_root", fail_switch)
    job = models_location.MoveJob()
    job._run(old, new, None)
    assert job.state["phase"] == "error"
    assert unrelated.read_bytes() == b"not-owned"
    assert list(new.rglob("*.part")) == [unrelated]
    assert source.read_bytes() == b"model-data"


def test_failed_source_open_closes_owned_temp_before_cleanup(repo, tmp_path, monkeypatch):
    import builtins

    old = tmp_path / "old"
    source = old / "models" / "weights.bin"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"model-data")
    new = tmp_path / "new"
    config.set_models_root(old)
    real_open = builtins.open

    def fail_source(file, *args, **kwargs):
        if Path(file) == source:
            raise OSError("synthetic source open failure")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", fail_source)
    job = models_location.MoveJob()
    job._run(old, new, None)
    assert job.state["phase"] == "error"
    assert source.read_bytes() == b"model-data"
    assert not list(new.rglob("*.part"))


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
