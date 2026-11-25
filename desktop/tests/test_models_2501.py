# -*- coding: utf-8 -*-
"""2.5.0.1 fixer 1 (models/updater):
- files_to_fetch counts every missing file of the EFFECTIVE (set-filtered) manifest, even when the raw installed manifest
  is an older/smaller one or the install is partial;
- update_status reports bytes_to_download > 0 whenever weights_update/weights_missing is true (the "0% then reverts" bug);
- is_complete checks the EFFECTIVE manifest (selected sets), not the raw all-file list.
"""
import json
import time

from linda_desktop import config, updater


def _entry(path, size, setname, sha):
    return {"path": path, "size": size, "sha256": sha, "set": setname}


def _old_manifest():
    """Old 1.3.4.1-style manifest: 34 shared files, no set split."""
    files = [_entry(f"models/old_{i:02d}/w.bin", 100, "shared", f"{i:064x}") for i in range(34)]
    return {"schema": 1, "version": "1.3.4.1", "files": files}


def _lean_manifest():
    """Lean latest.json: 61 files with set split (pro/lite/shared)."""
    files = []
    for i in range(25):
        files.append(_entry(f"models/essay_dhi_{i:02d}/w.bin", 1000, "pro", f"a{i:063x}"))
    for i in range(16):
        files.append(_entry(f"models/linda_speed_{i:02d}/w.bin", 500, "lite", f"b{i:063x}"))
    for i in range(20):
        files.append(_entry(f"calibration/c_{i:02d}.json", 50, "shared", f"c{i:063x}"))
    return {"schema": 1, "version": "2.0.0.1", "files": files}


def _write(root, manifest):
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _touch(root, entry):
    p = root / entry["path"]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\0" * entry["size"])


def _patch(monkeypatch, tmp_path, sets):
    home = tmp_path / "home"
    models = tmp_path / "models"
    monkeypatch.setenv("LINDA_HOME", str(home))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(models))
    home.mkdir(parents=True, exist_ok=True)
    (home / "settings.json").write_text(json.dumps({"model_sets": sets}), encoding="utf-8")
    return models


def test_files_to_fetch_counts_all_effective_missing(monkeypatch, tmp_path):
    models = _patch(monkeypatch, tmp_path, ["pro"])
    _write(models, _old_manifest())  # installed raw manifest is old & smaller
    lean = _lean_manifest()
    eff = updater.effective(lean)  # set-split: pro + shared only
    todo = updater.files_to_fetch(eff, models)
    expected = [f for f in lean["files"] if f.get("set", "shared") in ("shared", "pro")]
    assert len(todo) == len(expected) == 45


def test_files_to_fetch_partial_install(monkeypatch, tmp_path):
    models = _patch(monkeypatch, tmp_path, ["pro", "lite"])
    lean = _lean_manifest()
    eff = updater.effective(lean)
    _write(models, {**lean, "version": "2.0.0.1"})
    for f in lean["files"][:30]:  # partial install: only the first 30 present
        _touch(models, f)
    todo = updater.files_to_fetch(eff, models)
    assert len(todo) == len(lean["files"]) - 30 == 31


def test_update_status_bytes_positive_on_weights_update(monkeypatch, tmp_path):
    models = _patch(monkeypatch, tmp_path, ["pro"])
    _write(models, _old_manifest())
    lean_eff = updater.effective(_lean_manifest())
    st = updater.update_status(lean_eff)
    assert st["weights_update"] is True
    assert st["bytes_to_download"] > 0


def test_update_status_weights_missing_partial(monkeypatch, tmp_path):
    models = _patch(monkeypatch, tmp_path, ["pro", "lite"])
    lean = _lean_manifest()
    _write(models, lean)
    _touch(models, lean["files"][0])
    eff = updater.effective(lean)
    st = updater.update_status(eff)
    assert st["weights_missing"] is True
    assert st["bytes_to_download"] == sum(f["size"] for f in lean["files"][1:])


def test_is_complete_effective_not_raw(monkeypatch, tmp_path):
    models = _patch(monkeypatch, tmp_path, ["lite"])  # only lite selected
    lean = _lean_manifest()
    _write(models, lean)
    for f in lean["files"]:  # full disk state
        _touch(models, f)
    eff = updater.effective(lean)
    assert updater.is_complete(eff, models) is True
    raw = dict(lean)
    assert updater.is_complete(raw, models) is True
    # partial: lite files present, pro missing -> effective complete, raw not
    for f in lean["files"]:
        if f.get("set") == "pro":
            (models / f["path"]).unlink()
    assert updater.is_complete(updater.effective(lean), models) is True
    assert updater.is_complete(lean, models) is False


def test_optional_routing_with_lite_404_skips_with_warning(monkeypatch, tmp_path):
    """If calibration/routing.with_lite.json 404s on server, Job skips it with warning instead of hard-failing."""
    import base64
    import hashlib
    import http.server
    import threading
    import time
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    home = tmp_path / "home"
    models = tmp_path / "models"
    srv_root = tmp_path / "srv"
    home.mkdir(parents=True)
    models.mkdir(parents=True)
    (srv_root / "calibration").mkdir(parents=True)
    (home / "settings.json").write_text(json.dumps({"model_sets": ["lite"]}), encoding="utf-8")

    routing_bytes = b'{"kind": "merged", "voice_dirs": {}, "languages": {}}'
    (srv_root / "calibration" / "routing.json").write_bytes(routing_bytes)
    with_lite_bytes = b'{"kind": "merged", "voice_dirs": {"speed_s": "linda_speed_131"}, "languages": {}}'

    files = [
        {"path": "calibration/routing.json", "size": len(routing_bytes),
         "sha256": hashlib.sha256(routing_bytes).hexdigest(), "set": "shared"},
        {"path": "calibration/routing.with_lite.json", "size": len(with_lite_bytes),
         "sha256": hashlib.sha256(with_lite_bytes).hexdigest(), "set": "shared"},
    ]
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    manifest = {"schema": 1, "version": "1.5.0", "files": files}
    raw = json.dumps(manifest).encode("utf-8")
    sig = base64.b64encode(key.sign(raw))

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            rel = self.path.lstrip("/")
            if rel == "latest.json":
                data = raw
            elif rel == "latest.json.sig":
                data = sig
            else:
                p = srv_root / rel
                if not p.is_file():
                    self.send_error(404)
                    return
                data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("LINDA_HOME", str(home))
        monkeypatch.setenv("LINDA_MODELS_HOME", str(models))
        monkeypatch.setenv("LINDA_DEV", "1")
        monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", pub)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        m, m_raw = updater.get_manifest(base)
        job = updater.Job()
        assert job.start(m, m_raw, root=models, base_url=base)
        t0 = time.time()
        while job.running() and time.time() - t0 < 20:
            time.sleep(0.05)
        st = job.snapshot()
        assert st["phase"] == "done", st
        assert st["skipped_optional"] == ["calibration/routing.with_lite.json"]
        assert "routing.with_lite.json" in st["warning"]
        assert (models / "calibration" / "routing.json").is_file()
        assert updater.is_complete(m, models) is True
        assert updater.files_to_fetch(m, models) == []
    finally:
        srv.shutdown()
        srv.server_close()


def test_required_file_404_fails_with_filename(monkeypatch, tmp_path):
    """Non-optional 404 still fails with a clear error listing the missing file."""
    import base64
    import hashlib
    import http.server
    import threading
    import time
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    home = tmp_path / "home"
    models = tmp_path / "models"
    home.mkdir(parents=True)
    models.mkdir(parents=True)
    (home / "settings.json").write_text(json.dumps({"model_sets": ["lite"]}), encoding="utf-8")

    payload = b"missing-bin"
    files = [{"path": "models/linda_speed_131/model.onnx", "size": len(payload),
              "sha256": hashlib.sha256(payload).hexdigest(), "set": "lite"}]
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    raw = json.dumps({"schema": 1, "version": "1.5.0", "files": files}).encode("utf-8")
    sig = base64.b64encode(key.sign(raw))

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            if self.path == "/latest.json":
                data = raw
            elif self.path == "/latest.json.sig":
                data = sig
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("LINDA_HOME", str(home))
        monkeypatch.setenv("LINDA_MODELS_HOME", str(models))
        monkeypatch.setenv("LINDA_DEV", "1")
        monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", pub)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        m, m_raw = updater.get_manifest(base)
        job = updater.Job()
        job.start(m, m_raw, root=models, base_url=base)
        t0 = time.time()
        while job.running() and time.time() - t0 < 20:
            time.sleep(0.05)
        st = job.snapshot()
        assert st["phase"] == "error"
        assert "models/linda_speed_131/model.onnx" in st["error"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_engine_routing_with_lite_fallback(monkeypatch, tmp_path, caplog):
    """Engine falls back to calibration/routing.json with a warning when routing.with_lite.json is missing."""
    import logging
    from linda_desktop.engine import Engine

    home = tmp_path / "home"
    cal = home / "calibration"
    cal.mkdir(parents=True)
    (cal / "routing.json").write_text('{"kind": "merged", "voice_dirs": {}, "languages": {}}', encoding="utf-8")
    monkeypatch.setenv("LINDA_HOME", str(home))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(home))
    monkeypatch.delenv("LINDA_ROUTING", raising=False)

    eng = Engine()
    assert eng.calibration_file() is None  # routing files are not classic 1.1 calibrations
    with caplog.at_level(logging.WARNING, logger="linda.engine"):
        got = eng.routing_with_lite_file()
    assert got is not None and got.name == "routing.json"
    assert any("routing.with_lite.json" in rec.message for rec in caplog.records)

    (cal / "routing.with_lite.json").write_text('{"kind": "merged", "voice_dirs": {"speed_s": "linda_speed_131"}, "languages": {}}', encoding="utf-8")
    assert eng.calibration_file() is None
    assert eng.routing_with_lite_file().name == "routing.with_lite.json"


# ---- Bug 1 (2.5.0.1): "Update models" -> 32 MB -> 0% -> button returns -------------------------------

def _serve(tmp_path, lean, files_bytes, monkeypatch):
    """Signed local repo; returns (base_url, server). files_bytes: {path: bytes}."""
    import base64
    import http.server
    import threading
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    srv_root = tmp_path / "srv"
    for rel, data in files_bytes.items():
        p = srv_root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    key = Ed25519PrivateKey.generate()
    pub = base64.b64encode(key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    raw = json.dumps(lean).encode("utf-8")
    sig = base64.b64encode(key.sign(raw))

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            rel = self.path.lstrip("/").split("?")[0]
            data = raw if rel == "latest.json" else sig if rel == "latest.json.sig" else None
            if data is None:
                p = srv_root / rel
                if not p.is_file():
                    self.send_error(404)
                    return
                data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("LINDA_DEV", "1")
    monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", pub)
    return f"http://127.0.0.1:{srv.server_address[1]}", srv


def _reused_install(tmp_path, monkeypatch, new_files=8):
    """Disk: old 1.3.4.1 install whose own manifest claims the NEW hashes for the big file (installer reuse) while the bytes
    on disk are the old ones. Server: that big file with new bytes + N new small files."""
    import hashlib

    home, models = tmp_path / "home", tmp_path / "models"
    home.mkdir(parents=True)
    models.mkdir(parents=True)
    (home / "settings.json").write_text(json.dumps({"model_sets": ["pro"]}), encoding="utf-8")
    monkeypatch.setenv("LINDA_HOME", str(home))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(models))

    old_big, new_big = b"OLD" * 400_000, b"NEW" * 400_000  # same size, different bytes -> looks present
    assert len(old_big) == len(new_big)
    p = models / "models/pro_big/model.onnx"
    p.parent.mkdir(parents=True)
    p.write_bytes(old_big)

    files = [{"path": "models/pro_big/model.onnx", "size": len(new_big),
              "sha256": hashlib.sha256(new_big).hexdigest(), "set": "pro"}]
    served = {"models/pro_big/model.onnx": new_big}
    for i in range(new_files):
        data = ("new-%02d" % i).encode() * 60_000
        served[f"calibration/new_{i:02d}.json"] = data
        files.append({"path": f"calibration/new_{i:02d}.json", "size": len(data),
                      "sha256": hashlib.sha256(data).hexdigest(), "set": "shared"})
    (models / "manifest.json").write_text(json.dumps({"schema": 1, "version": "1.3.4.1", "files": files}), encoding="utf-8")
    lean = {"schema": 1, "version": "2.0.0.1", "files": files}
    return models, lean, served, new_big


def _wait(job, limit=60):
    t0 = time.time()
    samples = []
    while job.running() and time.time() - t0 < limit:
        s = job.snapshot()
        samples.append((s["phase"], s["done"], s["total"]))
        time.sleep(0.003)
    return samples


def test_reused_install_same_size_different_bytes_is_refetched(monkeypatch, tmp_path):
    """A reused install can hold a file of the right size but wrong bytes while its old manifest even claims the new hash.
    The cheap (trusting) pass reproduces the bug: the big file is skipped and only the small diff remains."""
    models, lean, served, new_big = _reused_install(tmp_path, monkeypatch)
    eff = updater.effective(lean)
    cheap = {f["path"] for f in updater.files_to_fetch(eff, models, verify=False)}
    assert "models/pro_big/model.onnx" not in cheap  # the trust bug, reproduced
    assert len(cheap) == len(lean["files"]) - 1  # only the new small files: the "32 MB" job
    todo = updater.files_to_fetch(eff, models)  # version moved -> verifies by default
    assert "models/pro_big/model.onnx" in {f["path"] for f in todo}
    assert len(todo) == len(lean["files"])
    # the verified pass left a .ok marker on the good file; the next check is cheap and does not downgrade the verdict
    after = {f["path"] for f in updater.files_to_fetch(eff, models)}
    assert "models/pro_big/model.onnx" in after and len(after) == len(todo)


def test_update_status_does_not_promise_zero_bytes_for_a_reused_install(monkeypatch, tmp_path):
    """The banner must never show 0 bytes for a reused install. It now reports a floor (the small diff); the job's own total
    grows to the real figure once it re-hashes the files the old manifest merely claimed were identical."""
    models, lean, served, new_big = _reused_install(tmp_path, monkeypatch)
    st = updater.update_status(updater.effective(lean))
    assert st["weights_update"] is True
    assert st["bytes_to_download"] == sum(f["size"] for f in lean["files"]) - len(new_big) > 0
    assert st["files_to_download"] == len(lean["files"]) - 1


def test_job_progress_moves_and_ends_at_100_percent(monkeypatch, tmp_path):
    """The symptom: 0% while bytes arrive, then the button returns. Progress must track fetched bytes and finish at total."""
    models, lean, served, new_big = _reused_install(tmp_path, monkeypatch)
    base, srv = _serve(tmp_path, lean, served, monkeypatch)
    try:
        m, raw = updater.get_manifest(base)
        job = updater.Job()
        job.start(m, raw, root=models, base_url=base)
        samples = [(d, t) for p, d, t in _wait(job) if p in ("downloading", "verifying", "applying", "finishing", "done")]
        st = job.snapshot()
        assert st["phase"] == "done", st
        total = sum(f["size"] for f in lean["files"])
        assert st["done"] == st["total"] == total
        assert samples and max(d for d, _ in samples) == total
        assert all(b >= a for (a, _), (b, _) in zip(samples, samples[1:])), "progress went backwards"
        assert any(0 < d < total for d, _ in samples), "progress never showed partial bytes"
        assert (models / "models/pro_big/model.onnx").read_bytes() == new_big  # the 'present' file really was replaced
    finally:
        srv.shutdown()


def test_job_never_reports_done_with_files_missing(monkeypatch, tmp_path):
    """If downloading silently produces nothing, the job must fail loudly instead of 'done' + a returning button."""
    models, lean, served, new_big = _reused_install(tmp_path, monkeypatch)
    base, srv = _serve(tmp_path, lean, served, monkeypatch)
    try:
        m, raw = updater.get_manifest(base)

        def fake_ok(self, f, staging, b, t0):
            return True  # pretends success, writes nothing

        job = updater.Job()
        monkeypatch.setattr(updater.Job, "_download_to", fake_ok)
        job.start(m, raw, root=models, base_url=base)
        _wait(job, 30)
        st = job.snapshot()
        assert st["phase"] == "error", st
        assert "incomplete" in st["error"] or "missing" in st["error"] or "checksum" in st["error"]
        assert updater.is_complete(m, models) is False
    finally:
        srv.shutdown()


def test_version_bump_with_identical_files_still_applies(monkeypatch, tmp_path):
    """Reuse case: nothing to download but the version moved. The job must adopt the version instead of offering the update forever."""
    import hashlib

    home, models = tmp_path / "home", tmp_path / "models"
    home.mkdir(parents=True)
    models.mkdir(parents=True)
    (home / "settings.json").write_text(json.dumps({"model_sets": ["pro"]}), encoding="utf-8")
    monkeypatch.setenv("LINDA_HOME", str(home))
    monkeypatch.setenv("LINDA_MODELS_HOME", str(models))
    files, served = [], {}
    for i in range(5):
        data = ("keep-%d" % i).encode() * 1000
        p = models / f"models/m_{i}/model.onnx"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        files.append({"path": f"models/m_{i}/model.onnx", "size": len(data),
                      "sha256": hashlib.sha256(data).hexdigest(), "set": "pro"})
        served[f"models/m_{i}/model.onnx"] = data
    (models / "manifest.json").write_text(json.dumps({"schema": 1, "version": "1.3.4.1", "files": files}), encoding="utf-8")
    lean = {"schema": 1, "version": "2.0.0.1", "files": files}
    base, srv = _serve(tmp_path, lean, served, monkeypatch)
    try:
        m, raw = updater.get_manifest(base)
        assert updater.files_to_fetch(m, models, verify=True) == []
        job = updater.Job()
        job.start(m, raw, root=models, base_url=base)
        _wait(job, 30)
        assert job.snapshot()["phase"] == "done", job.snapshot()
        assert updater.installed_version() == "2.0.0.1"
        assert updater.update_status(m)["weights_update"] is False
    finally:
        srv.shutdown()
