# -*- coding: utf-8 -*-
"""E2E update-pipeline tests against a LOCAL fake server (127.0.0.1) with an ephemeral Ed25519 keypair.

Covers: signed manifest fetch, update_status (weights_update/app_new), background download via staging,
signature rejection of a tampered manifest, staged installer accepted only with valid sig+checksum,
old staging cleanup, and the owner's 2.3.0.2 situation (remote == installed -> no update offered).
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from linda_desktop import config, updater


@pytest.fixture()
def keys():
    sk = Ed25519PrivateKey.generate()
    pub_b64 = base64.b64encode(sk.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")
    return sk, pub_b64


def sign(sk, raw: bytes) -> bytes:
    return base64.b64encode(sk.sign(raw))


def make_manifest(version, files, installer=None, min_app="0"):
    m = {"schema": 1, "version": version, "released": "2026-11-21", "channel": "stable",
         "min_app": min_app, "files": files, "notes": "test"}
    if installer:
        m["installer"] = installer
    return m


def model_file_entry(root: Path, rel: str, content: bytes):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(content)
    return {"path": rel, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}


class FakeServer:
    """Loopback server: serves latest.json/.sig and file bytes from a directory."""

    def __init__(self, serve_dir: Path, raw: bytes, sig: bytes):
        self.serve_dir = serve_dir
        self.raw = raw
        self.sig = sig
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if self.path == "/latest.json":
                    body = outer.raw
                elif self.path == "/latest.json.sig":
                    body = outer.sig
                else:
                    f = (outer.serve_dir / self.path.lstrip("/")).resolve()
                    if f.is_file() and str(f).startswith(str(outer.serve_dir.resolve())):
                        body = f.read_bytes()
                    else:
                        self.send_error(404)
                        return
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_HEAD(self):
                self.send_response(200)
                self.end_headers()

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture()
def env(tmp_path, monkeypatch, keys):
    """Isolate config: fake models root, fake pubkey, dev loopback allowed."""
    sk, pub = keys
    root = tmp_path / "data"
    (root / "models").mkdir(parents=True)
    monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", pub)
    monkeypatch.setattr(config, "BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setattr(config, "APP_VERSION", "2.3.0.2")
    monkeypatch.setattr(config, "models_root", lambda: root)
    monkeypatch.setattr(config, "data_dir", lambda: root)
    monkeypatch.setattr(config, "is_store_package", lambda: False)
    monkeypatch.setenv("LINDA_DEV", "1")
    monkeypatch.delenv("LINDA_ALLOW_HTTP", raising=False)
    monkeypatch.setenv("LINDA_ALLOW_HTTP", "1")
    return sk, root


def install_old_version(root: Path, version="1.3.4.1"):
    content = b"old-weights"
    entry = {"path": "models/linda_essay_v1.bin", "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    (root / "models/linda_essay_v1.bin").write_bytes(content)
    m = make_manifest(version, [entry])
    (root / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    return entry


def test_update_offered_and_downloaded_end_to_end(env, tmp_path):
    sk, root = env
    serve = tmp_path / "serve"
    new_content = b"new-weights-9.9.9"
    entry = model_file_entry(serve, "models/linda_essay_v2.bin", new_content)
    old = install_old_version(root)
    installer = {"version": "9.9.9", "app_id": "TEST-APP-ID", "url": "https://example.invalid/setup.exe",
                 "size": 10, "sha256": "0" * 64}
    m = make_manifest("9.9.9", [entry], installer=installer, min_app="2.3.0.2")
    raw = json.dumps(m).encode()
    srv = FakeServer(serve, raw, sign(sk, raw))
    try:
        manifest, raw2 = updater.get_manifest(srv.url)
        assert manifest["version"] == "9.9.9"
        st = updater.update_status(manifest)
        assert st["weights_update"] is True
        assert st["app_new"] is True
        assert st["app_required"] is False
        assert st["installer"]["version"] == "9.9.9"
        job = updater.Job()
        assert job.start(manifest, raw2, root=root, base_url=srv.url)
        for _ in range(300):
            if job.snapshot()["phase"] in ("done", "error", "cancelled"):
                break
            time.sleep(0.05)
        snap = job.snapshot()
        assert snap["phase"] == "done", snap
        assert (root / "models/linda_essay_v2.bin").read_bytes() == new_content
        assert updater.installed_version() == "9.9.9"
        assert not updater.staging_dir("9.9.9", root).exists()  # applied staging removed
    finally:
        srv.stop()


def test_same_version_no_update_offered(env, tmp_path):
    """Reproduces the owner's 2.3.0.2: remote weights == installed and installer <= app -> nothing offered."""
    sk, root = env
    serve = tmp_path / "serve"
    entry = model_file_entry(serve, "models/linda_essay_v1.bin", b"old-weights")
    install_old_version(root, "1.3.4.1")
    installer = {"version": "2.3.0.1", "app_id": "X", "url": "https://example.invalid/s.exe", "size": 1, "sha256": "0" * 64}
    m = make_manifest("1.3.4.1", [entry], installer=installer, min_app="2.0.3.7")
    raw = json.dumps(m).encode()
    srv = FakeServer(serve, raw, sign(sk, raw))
    try:
        manifest, _ = updater.get_manifest(srv.url)
        st = updater.update_status(manifest)
        assert st["weights_update"] is False
        assert st["app_new"] is False
        assert st["app_required"] is False
        assert st["installer"] is None
    finally:
        srv.stop()


def test_tampered_manifest_rejected(env, tmp_path):
    sk, root = env
    install_old_version(root)
    m = make_manifest("9.9.9", [])
    raw = json.dumps(m).encode()
    tampered = raw.replace(b"9.9.9", b"8.8.8")
    srv = FakeServer(tmp_path / "serve", tampered, sign(sk, raw))  # sig over original, body tampered
    try:
        with pytest.raises(updater.UpdateError, match="signature"):
            updater.get_manifest(srv.url)
    finally:
        srv.stop()


def test_staged_installer_requires_valid_sig_and_checksum(env, tmp_path):
    sk, root = env
    install_old_version(root)
    exe = b"fake-installer-bytes"
    info = {"version": "9.9.9", "app_id": config.DEV_APP_ID, "url": "https://example.invalid/setup.exe",
            "size": len(exe), "sha256": hashlib.sha256(exe).hexdigest()}
    m = make_manifest("9.9.9", [], installer=info)
    m["channel"] = "dev"
    raw = json.dumps(m).encode()
    sig = sign(sk, raw).decode()
    # local "download" straight into staging
    staging = updater.staging_dir("9.9.9", root)
    staging.mkdir(parents=True)
    dest = updater.download_installer.__wrapped__ if hasattr(updater.download_installer, "__wrapped__") else None
    # write the exe the same way download_installer does, then build metadata
    (staging / updater.INSTALLER_NAME).write_bytes(exe)
    meta = {"version": "9.9.9", "ts": time.time(), "sha256": info["sha256"], "size": len(exe),
            "manifest": base64.b64encode(raw).decode(), "signature": sig}
    (staging / updater.INSTALLER_READY_NAME).write_text(json.dumps(meta), encoding="utf-8")
    st = updater.staged_installer(root)
    assert st is not None and st["version"] == "9.9.9"
    updater.verify_staged_installer(st)  # must not raise
    # tamper: corrupt signature -> rejected
    meta["signature"] = base64.b64encode(b"bad" * 22).decode()
    (staging / updater.INSTALLER_READY_NAME).write_text(json.dumps(meta), encoding="utf-8")
    with pytest.raises(updater.UpdateError):
        updater.verify_staged_installer(st)
    # tamper: corrupt exe -> checksum rejected
    meta["signature"] = sig
    (staging / updater.INSTALLER_READY_NAME).write_text(json.dumps(meta), encoding="utf-8")
    (staging / updater.INSTALLER_NAME).write_bytes(exe + b"x")
    with pytest.raises(updater.UpdateError, match="checksum"):
        updater.verify_staged_installer(st)


def test_old_staging_cleaned(env, tmp_path):
    sk, root = env
    install_old_version(root)
    # stale staging dir with an installer older than APP_VERSION (2.3.0.2)
    stale = updater.staging_dir("2.0.0.0", root)
    stale.mkdir(parents=True)
    (stale / updater.INSTALLER_NAME).write_bytes(b"old")
    (stale / updater.INSTALLER_READY_NAME).write_text(json.dumps(
        {"version": "2.0.0.0", "sha256": "0" * 64, "size": 3}), encoding="utf-8")
    assert updater.staged_installer(root) is None
    assert not stale.exists()  # removed as stale
