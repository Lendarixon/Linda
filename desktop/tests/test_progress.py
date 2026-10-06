# -*- coding: utf-8 -*-
"""Прогресс проверки: сервер отдаёт проценты по job_id, движок сообщает этапы."""
from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, engine as engine_mod, updater


def test_progress_endpoint_and_report(repo, monkeypatch):
    monkeypatch.setattr(updater, "is_complete", lambda: True)
    core = app_mod.Core()
    seen = []

    def run(text, mode, models, cancellable=False, cancel=None, progress=None):
        progress(10, "load"); progress(55, "scan")
        seen.append(core.progress.get("job1"))
        return {"verdict": "human", "p_ai": .1, "sentences": []}

    monkeypatch.setattr(core.engine, "run", run)
    with TestClient(app_mod.create_app(core, token="t")) as c:
        c.headers["x-linda-token"] = "t"
        assert c.get("/api/progress/nothing").json() == {"pct": 0, "phase": "wait"}
        assert c.get("/api/progress/bad id!").status_code == 400
        r = c.post("/api/detect", json={"text": "word " * 40, "job_id": "job1", "client_id": "tab1", "save": False})
        assert r.status_code == 200
    assert seen[0]["pct"] == 55 and seen[0]["phase"] == "scan"
    assert "job1" not in core.progress  # запись убирается после проверки


def test_engine_emits_stages():
    eng = engine_mod.Engine()
    got = []
    eng._progress_cb = lambda pct, phase: got.append((pct, phase))
    eng._emit(5, "load"); eng._emit(150, "scan"); eng._emit(-4, "sent")
    assert got == [(5.0, "load"), (100.0, "scan"), (0.0, "sent")]
