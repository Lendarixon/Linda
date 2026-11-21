# -*- coding: utf-8 -*-
import base64
import hashlib
import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from linda_desktop import config, updater

BIG = bytes(range(256)) * 4000  # ~1 MB
FILES1 = {"models/a/model.bin": BIG, "models/a/config.json": b'{"x":1}', "calibration/cal.json": b'{"v":1}'}


def run_job(manifest, raw, timeout=30):
    job = updater.Job()
    job.start(manifest, raw)
    t0 = time.time()
    while job.running() and time.time() - t0 < timeout:
        time.sleep(0.05)
    return job.snapshot()


def test_fresh_install_and_status(repo):
    repo.publish(FILES1, "1.1.0")
    m, raw = updater.get_manifest()
    assert updater.update_status(m)["weights_missing"]
    st = run_job(m, raw)
    assert st["phase"] == "done", st
    assert updater.is_complete() and updater.installed_version() == "1.1.0"
    assert (config.data_dir() / "models/a/model.bin").read_bytes() == BIG
    s2 = updater.update_status(m)
    assert not s2["weights_missing"] and not s2["weights_update"]


def test_update_downloads_only_changed_files_and_cleans_stale(repo):
    repo.publish(FILES1, "1.1.0")
    m, raw = updater.get_manifest()
    assert run_job(m, raw)["phase"] == "done"
    repo.log.clear()
    new = {"models/a/model.bin": BIG, "models/a/config.json": b'{"x":2}', "calibration/cal2.json": b'{"v":2}'}  # config changed, calibration renamed
    repo.publish(new, "1.1.1", notes="fresh humanizers")
    m2, raw2 = updater.get_manifest()
    s = updater.update_status(m2)
    assert s["weights_update"] and s["notes"] == "fresh humanizers"
    st = run_job(m2, raw2)
    assert st["phase"] == "done", st
    fetched = {r for r, _ in repo.log if not r.startswith("latest")}
    assert fetched == {"models/a/config.json", "calibration/cal2.json"}  # the 1 MB weights were NOT downloaded again
    assert updater.installed_version() == "1.1.1"
    assert not (config.data_dir() / "calibration/cal.json").exists()  # stale file removed


def test_tampered_file_rejected(repo):
    repo.publish(FILES1, "1.1.0")
    (repo.root / "models/a/model.bin").write_bytes(BIG[:-1] + b"X")  # same size, different content
    m, raw = updater.get_manifest()
    st = run_job(m, raw)
    assert st["phase"] == "error" and "checksum" in st["error"]
    assert not updater.installed_version()
    assert not (config.data_dir() / "models/a/model.bin").exists()


def test_bad_signature_rejected(repo):
    repo.publish(FILES1, "1.1.0")
    (repo.root / "latest.json").write_bytes((repo.root / "latest.json").read_bytes().replace(b"1.1.0", b"9.9.9"))
    with pytest.raises(updater.UpdateError, match="signature"):
        updater.get_manifest()


def test_wrong_key_rejected(repo, monkeypatch):
    repo.publish(FILES1, "1.1.0")
    other = base64.b64encode(Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
    monkeypatch.setattr(config, "SIGNING_PUBKEY_B64", other)
    with pytest.raises(updater.UpdateError, match="signature"):
        updater.get_manifest()


def test_resume_after_dropped_connection(repo):
    repo.publish(FILES1, "1.1.0")
    repo.fail_once["models/a/model.bin"] = True
    m, raw = updater.get_manifest()
    st = run_job(m, raw)
    assert st["phase"] == "done", st
    assert (config.data_dir() / "models/a/model.bin").read_bytes() == BIG
    starts = [s for r, s in repo.log if r == "models/a/model.bin"]
    assert len(starts) == 2 and starts[1] > 0  # the second request resumed from the middle


def test_path_traversal_rejected(repo):
    repo.publish({"../evil.txt": b"x"}, "1.1.0")
    with pytest.raises(updater.UpdateError, match="malformed"):
        updater.get_manifest()


def test_app_required_and_installer_info(repo):
    repo.publish(FILES1, "1.2.0", min_app="9.0.0", installer={"version": "9.0.0", "url": "https://example.invalid/Linda-Setup.exe", "size": 5, "sha256": "0" * 64})
    m, _ = updater.get_manifest()
    s = updater.update_status(m)
    assert s["app_required"] and s["app_new"] and s["installer"]["version"] == "9.0.0"


def test_installer_hash_checked(repo, monkeypatch):
    monkeypatch.setenv("LINDA_ALLOW_HTTP", "1")
    payload = b"MZ" + b"\0" * 5000
    (repo.root / "Linda-Setup.exe").write_bytes(payload)
    ok = {"url": repo.url + "/Linda-Setup.exe", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
    assert updater.download_installer(ok).read_bytes() == payload
    with pytest.raises(updater.UpdateError, match="checksum"):
        updater.download_installer({**ok, "sha256": "1" * 64})
    monkeypatch.delenv("LINDA_ALLOW_HTTP")
    with pytest.raises(updater.UpdateError, match="https"):
        updater.download_installer(ok)


def test_corrupted_local_file_is_redownloaded(repo):
    repo.publish(FILES1, "1.1.0")
    m, raw = updater.get_manifest()
    run_job(m, raw)
    (config.data_dir() / "models/a/config.json").write_bytes(b'{"x":9}')  # same size, corrupted
    (config.data_dir() / "manifest.json").unlink()  # forces hash verification
    assert [f["path"] for f in updater.files_to_fetch(m)] == ["models/a/config.json"]


def test_server_unreachable(repo):
    repo.srv.shutdown()
    repo.srv.server_close()
    with pytest.raises(updater.UpdateError, match="cannot reach|update"):
        updater.get_manifest()


def test_is_complete_survives_os_errors(repo, monkeypatch):
    repo.publish(FILES1, "1.1.0")
    m, raw = updater.get_manifest()
    assert run_job(m, raw)["phase"] == "done" and updater.is_complete()

    def boom(self):
        raise OSError(448, "untrusted mount point")

    monkeypatch.setattr(type(config.data_dir()), "is_file", boom)
    assert updater.is_complete() is False  # no crash
