# -*- coding: utf-8 -*-
"""Обновление «перезапустите»: скачанный инсталлер находится, устаревший чистится, /api/app/restart запускает его и завершает процесс."""
from pathlib import Path
import hashlib
import json
import threading
import base64

from fastapi.testclient import TestClient

from linda_desktop import app as app_mod
from linda_desktop import config, updater

TOKEN = "t0k"


def _stage(root: Path, ver: str, ready=True, repo=None):
    d = root / "staging" / ver
    d.mkdir(parents=True)
    (d / "Linda-Setup.exe").write_bytes(b"MZ" + b"0" * 100)
    if ready:
        payload = (d / 'Linda-Setup.exe').read_bytes()
        meta = {'sha256':hashlib.sha256(payload).hexdigest(),'size':len(payload)}
        if repo:
            raw = json.dumps({'installer':{'version':ver,**meta}}).encode()
            meta.update(manifest=base64.b64encode(raw).decode(),signature=base64.b64encode(repo.key.sign(raw)).decode())
        (d / updater.INSTALLER_READY_NAME).write_text(json.dumps(meta), encoding="utf-8")
    return d


def test_staged_installer_newer_found_stale_removed(tmp_path):
    new = _stage(tmp_path, "99.0.0")
    old = _stage(tmp_path, "0.0.1")
    unfinished = _stage(tmp_path, "98.0.0", ready=False)
    st = updater.staged_installer(tmp_path)
    assert st and st["version"] == "99.0.0" and Path(st["path"]).is_file()
    assert not old.exists() and unfinished.exists() and new.exists()


def test_restart_launches_staged_installer(repo, monkeypatch):
    _stage(config.data_dir(), "99.0.0", repo=repo)
    launched, exits = [], []
    finished = threading.Event()
    monkeypatch.setattr(app_mod, "launch_installer", lambda p: launched.append(Path(p)))
    monkeypatch.setattr(app_mod.os, "_exit", lambda c: (exits.append(c), finished.set()))
    monkeypatch.setattr(app_mod.time, "sleep", lambda s: None)
    c = TestClient(app_mod.create_app(app_mod.Core(), token=TOKEN), headers={"x-linda-token": TOKEN})
    st = c.get("/api/status").json()
    assert st["update_pending"]["version"] == "99.0.0"
    r = c.post("/api/app/restart")
    assert r.status_code == 200 and r.json()["status"] == "restarting"
    assert finished.wait(3)
    assert launched and launched[0].name == "Linda-Setup.exe" and exits == [0]


def test_restart_without_staged_is_409(repo):
    c = TestClient(app_mod.create_app(app_mod.Core(), token=TOKEN), headers={"x-linda-token": TOKEN})
    assert c.post("/api/app/restart").status_code == 409


def test_dev_rejects_production_channel_even_with_valid_signature(repo, monkeypatch):
    import pytest
    _stage(config.data_dir(), '99.0.0', repo=repo)
    monkeypatch.setenv('LINDA_DEV','1')
    with pytest.raises(updater.UpdateError, match='signed update proof'):
        updater.verify_staged_installer(updater.staged_installer())


def test_dev_accepts_only_its_signed_app_identity(repo, monkeypatch):
    import pytest
    stage = _stage(config.data_dir(), '99.0.0', repo=repo)
    metadata = json.loads((stage/updater.INSTALLER_READY_NAME).read_text())
    manifest = json.loads(base64.b64decode(metadata['manifest']))
    manifest['channel'] = 'dev'
    manifest['installer']['app_id'] = config.DEV_APP_ID
    def publish():
        raw = json.dumps(manifest).encode()
        metadata.update(manifest=base64.b64encode(raw).decode(), signature=base64.b64encode(repo.key.sign(raw)).decode())
        (stage/updater.INSTALLER_READY_NAME).write_text(json.dumps(metadata))
    publish()
    monkeypatch.setenv('LINDA_DEV','1')
    updater.verify_staged_installer(updater.staged_installer())
    manifest['installer']['app_id'] = 'production-app'
    publish()
    with pytest.raises(updater.UpdateError):
        updater.verify_staged_installer(updater.staged_installer())


def test_restart_does_not_discard_an_active_analysis(repo, monkeypatch):
    _stage(config.data_dir(), '99.0.0', repo=repo)
    core = app_mod.Core()
    core.engine.lock.acquire()
    try:
        c = TestClient(app_mod.create_app(core, token=TOKEN), headers={'x-linda-token':TOKEN})
        assert c.post('/api/app/restart').status_code == 409
        assert core.installer_job['phase'] != 'launching'
    finally:
        core.engine.lock.release()
