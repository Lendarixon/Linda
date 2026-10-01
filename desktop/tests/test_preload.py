# -*- coding: utf-8 -*-
import time

from fastapi.testclient import TestClient

from linda_desktop import updater
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


def make(monkeypatch, complete=True):
    core = Core()
    calls = []
    monkeypatch.setattr(updater, "is_complete", lambda *a, **k: complete)
    monkeypatch.setattr(core.engine, "ensure_loaded", lambda: calls.append(1) or {"x": 1})
    return core, calls


def wait(calls, n=1, t=3.0):
    t0 = time.time()
    while len(calls) < n and time.time() - t0 < t:
        time.sleep(0.02)


def test_preload_on_by_default(repo, monkeypatch):
    core, calls = make(monkeypatch)
    assert core.preload() is True
    wait(calls)
    assert calls == [1]


def test_preload_can_be_switched_off(repo, monkeypatch):
    core, calls = make(monkeypatch)
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    assert c.post("/api/settings", json={"preload": False}).json()["settings"]["preload"] is False
    assert core.preload() is False
    time.sleep(0.2)
    assert calls == []  # nothing is loaded until the first analysis
    assert c.get("/api/status").json()["settings"]["preload"] is False


def test_switching_on_loads_immediately(repo, monkeypatch):
    core, calls = make(monkeypatch)
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    c.post("/api/settings", json={"preload": False})
    c.post("/api/settings", json={"preload": True})
    wait(calls)
    assert calls == [1]


def test_no_preload_without_models_and_bad_value_ignored(repo, monkeypatch):
    core, calls = make(monkeypatch, complete=False)
    assert core.preload() is False
    c = TestClient(create_app(core, token=TOKEN), headers={"x-linda-token": TOKEN})
    assert "preload" not in c.post("/api/settings", json={"preload": "yes"}).json()["settings"]
    time.sleep(0.2)
    assert calls == []
