# -*- coding: utf-8 -*-
import http.server
import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from linda_desktop import config, licensing
from linda_desktop.app import Core, create_app

TOKEN = "t0k"


class FakePolar:
    def __init__(self):
        self.revoked = False
        self.calls = []
        self.activation_conditions = None
        self.deactivated = []
        me = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                me.calls.append((self.path, body))
                code, out = 200, {}
                if self.path.endswith("/deactivate"):
                    me.deactivated.append(body.get("activation_id"))
                    code, out = 204, {}
                elif self.path.endswith("/activate"):
                    if body["key"] == "LINDA-GOOD":
                        me.activation_conditions = body.get("conditions")
                        out = {"id": "act1", "license_key": {"status": "granted", "limit_activations": 20, "expires_at": None}}
                    elif body["key"] == "LINDA-FULL":
                        code, out = 403, {"detail": "License key activation limit already reached"}
                    else:
                        code, out = 404, {"detail": "Not found"}
                elif self.path.endswith("/validate"):
                    out = {"status": "revoked" if me.revoked else "granted", "expires_at": None}
                    if body.get("conditions") != me.activation_conditions:  # like Polar: conditions must match the activation
                        code, out = 404, {"detail": "Not found"}
                data = json.dumps(out).encode()
                self.send_response(code)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()


@pytest.fixture()
def polar(monkeypatch, repo):
    p = FakePolar()
    monkeypatch.setattr(config, "POLAR_API", p.url)
    monkeypatch.setattr(config, "POLAR_ORG_ID", "org-123")
    yield p
    p.srv.shutdown()


@pytest.fixture()
def client(repo):
    c = TestClient(create_app(Core(), token=TOKEN), headers={"x-linda-token": TOKEN})
    return c


def test_token_and_host_guard(repo):
    app = create_app(Core(), token=TOKEN)
    c = TestClient(app)
    assert c.get("/api/status").status_code == 403  # no token
    assert c.get("/api/status", headers={"x-linda-token": "wrong"}).status_code == 403
    assert c.get("/api/status", headers={"x-linda-token": TOKEN, "host": "evil.example.com"}).status_code == 403  # DNS rebinding
    assert c.get("/api/status", headers={"x-linda-token": TOKEN}).status_code == 200
    page = c.get("/").text
    assert TOKEN in page and "__LINDA_TOKEN__" not in page


def test_status_before_install_and_detect_refused(client):
    s = client.get("/api/status").json()
    assert s["models_ready"] is False and s["license"]["licensed"] is False
    r = client.post("/api/detect", json={"text": "word " * 100})
    assert r.status_code == 409


def test_upload_txt_and_limits(client):
    r = client.post("/api/upload", files={"file": ("a.txt", b"Hello world. " * 30, "text/plain")})
    assert r.status_code == 200 and r.json()["words"] == 60
    assert client.post("/api/upload", files={"file": ("a.exe", b"MZ", "application/octet-stream")}).status_code == 400
    assert client.post("/api/upload", files={"file": ("a.txt", b"   ", "text/plain")}).status_code == 400


def test_license_activate_and_errors(client, polar):
    r = client.post("/api/license/activate", json={"key": "LINDA-GOOD"})
    assert r.status_code == 200
    lic = r.json()["license"]
    assert lic["licensed"] and lic["tier"] == "team" and "LINDA-GOOD" not in lic["key_hint"]
    assert polar.calls[0][1]["organization_id"] == "org-123" and polar.calls[0][1]["label"].startswith("Windows-")
    assert client.get("/api/status").json()["license"]["licensed"]
    assert client.post("/api/license/remove").json()["license"]["licensed"] is False
    assert "device limit" in client.post("/api/license/activate", json={"key": "LINDA-FULL"}).json()["detail"]
    assert "not found" in client.post("/api/license/activate", json={"key": "nope"}).json()["detail"]
    assert client.post("/api/license/activate", json={"key": ""}).status_code == 422


def test_license_revalidate_revoked_and_offline(client, polar):
    client.post("/api/license/activate", json={"key": "LINDA-GOOD"})
    assert licensing.revalidate()["licensed"]  # not due yet: no network call
    n = len(polar.calls)
    polar.revoked = True
    assert licensing.revalidate()["licensed"] and len(polar.calls) == n  # still cached
    assert licensing.revalidate(force=True)["licensed"] is False  # revoked key stops being licensed
    polar.srv.shutdown()
    polar.srv.server_close()
    st = licensing.load()
    st.update(status="granted", last_validated=0)
    licensing._save(st)
    assert licensing.revalidate(force=True)["licensed"]  # offline keeps the cached state


def test_license_not_configured(client, monkeypatch):
    monkeypatch.setattr(config, "POLAR_ORG_ID", "")
    r = client.post("/api/license/activate", json={"key": "LINDA-GOOD"})
    assert r.status_code == 422 and "not configured" in r.json()["detail"]


def test_download_through_api_and_settings(client, repo):
    repo.publish({"models/a/m.bin": b"x" * 5000, "calibration/c.json": b"{}"}, "1.1.0")
    assert client.post("/api/update/check").json()["update"]["weights_missing"]
    assert client.post("/api/models/download").status_code == 200
    for _ in range(100):
        s = client.get("/api/status").json()
        if s["download"]["phase"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert s["download"]["phase"] == "done" and s["models_ready"] and s["installed_version"] == "1.1.0"
    assert client.post("/api/settings", json={"sentences": "windows", "device": "cpu"}).json()["settings"] == {"sentences": "windows", "device": "cpu"}
    assert client.post("/api/app/update").status_code == 409  # no app update announced


def test_app_required_blocks_download(client, repo):
    repo.publish({"models/a/m.bin": b"x" * 10, "calibration/c.json": b"{}"}, "2.0.0", min_app="9.0.0")
    client.post("/api/update/check")
    assert client.post("/api/models/download").status_code == 409


def test_machine_binding_blocks_a_copied_licence_file(client, polar, monkeypatch):
    client.post("/api/license/activate", json={"key": "LINDA-GOOD"})
    mine = licensing.machine_id()
    assert polar.calls[0][1]["conditions"] == {"machine": mine} and licensing.load()["machine"] == mine
    assert len(mine) == 24 and mine == licensing.machine_id()  # stable
    assert client.get("/api/status").json()["license"]["licensed"]
    # the same licence.json on a different computer: not licensed, even offline (no network involved)
    monkeypatch.setattr(licensing, "machine_id", lambda: "b" * 24)
    lic = client.get("/api/status").json()["license"]
    assert lic["licensed"] is False and lic["status"] == "other_machine"
    # someone edits the machine field to match the new computer: the server-side condition check rejects it at the next validation
    st = licensing.load()
    st["machine"] = "b" * 24
    licensing._save(st)
    assert licensing.revalidate(force=True)["licensed"] is False and licensing.load()["status"] == "revoked"
    assert polar.calls[-1][1]["conditions"] == {"machine": "b" * 24}


def test_remove_key_frees_the_device_slot(client, polar):
    client.post("/api/license/activate", json={"key": "LINDA-GOOD"})
    assert client.post("/api/license/remove").json()["license"]["licensed"] is False
    assert polar.deactivated == ["act1"]
    assert licensing.load() == {}
