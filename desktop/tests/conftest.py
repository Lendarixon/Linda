# -*- coding: utf-8 -*-
import base64
import hashlib
import http.server
import json
import sys
import threading
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class Repo:
    """A fake model repository served over HTTP with Range support and optional fault injection."""

    def __init__(self, root: Path):
        self.root, self.log, self.fail_once = root, [], {}
        self.key = Ed25519PrivateKey.generate()
        self.pub = base64.b64encode(self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        repo = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                rel = self.path.lstrip("/").split("?")[0]
                p = repo.root / rel
                if not p.is_file():
                    self.send_error(404)
                    return
                data = p.read_bytes()
                start = 0
                rng = self.headers.get("Range")
                if rng and rng.startswith("bytes="):
                    start = int(rng[6:].split("-")[0])
                repo.log.append((rel, start))
                self.send_response(206 if start else 200)
                self.send_header("Content-Length", str(len(data) - start))
                self.end_headers()
                body = data[start:]
                if repo.fail_once.pop(rel, False):  # send half, then drop the connection
                    self.wfile.write(body[: len(body) // 2])
                    self.wfile.flush()
                    self.connection.close()
                    return
                self.wfile.write(body)

        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def publish(self, files: dict, version: str, **extra):
        for rel, data in files.items():
            p = self.root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        m = {"schema": 1, "version": version, "min_app": extra.pop("min_app", "1.0.0"), "notes": extra.pop("notes", ""),
             "files": [{"path": r, "size": len(d), "sha256": hashlib.sha256(d).hexdigest()} for r, d in files.items()], **extra}
        raw = json.dumps(m).encode()
        (self.root / "latest.json").write_bytes(raw)
        (self.root / "latest.json.sig").write_bytes(base64.b64encode(self.key.sign(raw)))
        return m


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    r = Repo(tmp_path / "repo")
    r.root.mkdir()
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "home"))
    from linda_desktop import config

    monkeypatch.setattr(config, "BASE_URL", r.url)
    monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", r.pub)
    yield r
    r.srv.shutdown()
