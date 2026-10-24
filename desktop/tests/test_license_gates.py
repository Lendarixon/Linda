# -*- coding: utf-8 -*-
"""Licensed-only tools stay closed without a licence key (server side).

Trace/Humanizer/packs must refuse with 403 when unlicensed and let the
request through the gate when licensed (deeper errors like 400/409/500
prove the licence check passed).
"""
import json

import pytest
from fastapi.testclient import TestClient

from linda_desktop import config, licensing
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


@pytest.fixture()
def client(repo):
    return TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})


def test_licensed_only_endpoints_refuse_without_key(client):
    client.post("/api/settings", json={"language": "en"})
    assert client.post("/api/humanize", json={"text": "word " * 10}).status_code == 403
    assert client.post("/api/humanize/loop", json={"text": "word " * 10}).status_code == 403
    assert client.post("/api/trace/corpus", json={"documents": [{"id": "a", "text": "word " * 400}]}).status_code == 403
    assert client.post("/api/trace/authorship", json={"references": [], "documents": []}).status_code == 403
    assert client.post("/api/packs/download", json={"pack": "trace"}).status_code == 403


def test_licensed_requests_pass_the_gate(client, monkeypatch):
    monkeypatch.setattr(licensing, "public_state",
                        lambda st=None: {"licensed": True, "kind": "gift", "tier": "personal",
                                         "key_hint": "T", "status": "granted", "configured": True})
    # past the licence gate: validation/pack errors, but never 403
    # (ensure() raises before any download, so no network or disk side effects here)
    client.post("/api/settings", json={"language": "en"})
    assert client.post("/api/humanize", json={"text": "word " * 10}).status_code == 409
    assert client.post("/api/humanize/loop", json={"text": "word " * 10}).status_code != 403
    from linda_desktop import trace_pack
    monkeypatch.setattr(trace_pack, "installed", lambda: False)
    assert client.post("/api/trace/corpus", json={"documents": [{"id": "a", "text": "word " * 400}]}).status_code == 409
    assert client.post("/api/packs/download", json={"pack": "nope"}).status_code != 403


def test_licence_error_messages_localized(client):
    client.post("/api/settings", json={"language": "en"})
    r = client.post("/api/license/activate", json={"key": "nope"})
    assert r.status_code == 422 and "not found" in r.json()["detail"]
    client.post("/api/settings", json={"language": "ru"})
    r = client.post("/api/license/activate", json={"key": "nope"})
    assert r.status_code == 422 and "не найден" in r.json()["detail"]
    client.post("/api/settings", json={"language": "pl"})
    r = client.post("/api/license/activate", json={"key": ""})
    assert r.status_code == 422 and "Wpisz" in r.json()["detail"]


def test_missing_pack_errors_localized(client, monkeypatch):
    from linda_desktop import humanize_pack, trace_pack
    monkeypatch.setattr(licensing, "public_state",
                        lambda st=None: {"licensed": True, "kind": "gift", "tier": "personal",
                                         "key_hint": "T", "status": "granted", "configured": True})
    # паков нет: ensure/install падают до любой загрузки — проверяем именно тексты 409
    monkeypatch.setattr(humanize_pack, "installed", lambda variant="auto": False)
    monkeypatch.setattr(trace_pack, "installed", lambda: False)
    client.post("/api/settings", json={"language": "ru"})
    r = client.post("/api/humanize", json={"text": "word " * 10})
    assert r.status_code == 409 and "не скачан" in r.json()["detail"]
    r = client.post("/api/trace/corpus", json={"documents": [{"id": "a", "text": "x"}]})
    assert r.status_code == 409 and "не установлен" in r.json()["detail"]
