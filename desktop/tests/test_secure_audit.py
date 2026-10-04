"""Synthetic profiles only: native Windows DPAPI, chain edits and commit recovery."""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

from linda_desktop import secure_audit as audit


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("LINDA_HOME", str(tmp_path / "synthetic-audit"))
    return audit.config.data_dir()


def populated(home):
    audit.append("check", "private synthetic document")
    audit.append("export", "synthetic result")
    audit.append("check", "third")
    return home


def test_roundtrip_filter_and_exportable_checkpoint(home):
    populated(home)
    assert [r["id"] for r in audit.list_entries()] == [3, 2, 1]
    assert [r["id"] for r in audit.list_entries("check", 1, 1)] == [1]
    info = audit.integrity_info()
    assert info["ok"] and info["checkpoint"]["count"] == 3
    assert len(info["checkpoint"]["mac"]) == 64
    assert info["external_anchor"] is False
    for name in ("audit.ledger", "audit.key", "audit.checkpoint"):
        assert b"private synthetic document" not in (home / name).read_bytes()


@pytest.mark.parametrize("operation", ["edit", "reorder", "truncate", "delete_middle", "wipe_records"])
def test_ledger_tampering_fails_closed(home, operation):
    populated(home)
    path = home / "audit.ledger"
    rows = audit._read(path)
    if operation == "edit":
        rows[0]["detail"] = "changed"
    elif operation == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    elif operation == "truncate":
        rows.pop()
    elif operation == "delete_middle":
        rows.pop(1)
    else:
        rows = []
    # A fixture possessing the Windows user credential can re-encrypt files;
    # unchanged authentication/checkpoint must still expose these modifications.
    audit._write(path, rows)
    assert audit.integrity_info()["ok"] is False
    before = path.read_bytes()
    with pytest.raises(audit.AuditIntegrityError):
        audit.append("new", "must not hide damage")
    assert path.read_bytes() == before
    with pytest.raises(audit.AuditIntegrityError):
        audit.list_entries()


@pytest.mark.parametrize("name", ["audit.ledger", "audit.key", "audit.checkpoint"])
def test_partial_file_wipe_is_not_silently_reset(home, name):
    populated(home)
    (home / name).unlink()
    assert not audit.integrity_info()["ok"]
    with pytest.raises(audit.AuditIntegrityError):
        audit.append("reset", "no")


def test_ciphertext_corruption(home):
    populated(home)
    path = home / "audit.ledger"
    value = bytearray(path.read_bytes())
    value[-1] ^= 1
    path.write_bytes(value)
    assert not audit.integrity_info()["ok"]


@pytest.mark.parametrize("failed_write", ["audit.ledger", "audit.checkpoint"])
def test_crash_after_journal_or_ledger_commit_recovers(home, monkeypatch, failed_write):
    audit.append("first", "one")
    write = audit._write

    def crash(path, value):
        if path.name == failed_write:
            raise OSError("simulated process exit")
        return write(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(audit, "_write", crash)
        with pytest.raises(OSError):
            audit.append("second", "two")
    assert (home / "audit.pending").exists()
    assert [r["action"] for r in audit.list_entries()] == ["second", "first"]
    assert audit.integrity_info()["checkpoint"]["count"] == 2
    assert not (home / "audit.pending").exists()


def test_crash_after_checkpoint_commit_recovers(home, monkeypatch):
    audit.append("first")
    original = audit.Path.unlink

    def crash(path, *args, **kwargs):
        if path.name == "audit.pending":
            raise OSError("simulated exit before journal removal")
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(audit.Path, "unlink", crash)
        with pytest.raises(OSError):
            audit.append("second")
    assert audit.integrity_info()["ok"]
    assert len(audit.list_entries()) == 2


def test_pending_journal_cannot_mask_unrelated_rollback(home, monkeypatch):
    populated(home)
    write = audit._write
    with monkeypatch.context() as patch:
        def crash(path, value):
            if path.name == "audit.checkpoint":
                raise OSError("simulated crash")
            write(path, value)
        patch.setattr(audit, "_write", crash)
        with pytest.raises(OSError):
            audit.append("fourth")
    write(home / "audit.ledger", audit._read(home / "audit.ledger")[:1])
    assert not audit.integrity_info()["ok"]


def test_legacy_import_is_explicitly_unverified_and_idempotent(home):
    source = [{"id": 17, "ts": 123.0, "action": "old", "detail": "before chain"}]
    assert audit.migrate_legacy(source) == 1
    assert audit.migrate_legacy(source) == 0
    rows = audit.list_entries()
    assert rows[1]["legacy"] and rows[1]["ts"] == 123.0
    assert "legacy_id=17" in rows[1]["detail"]
    assert rows[0]["action"] == "audit_legacy_import"
    assert audit.integrity_info()["legacy_entries"] == 1
    with pytest.raises(audit.AuditIntegrityError):
        audit.migrate_legacy([{**source[0], "detail": "different"}])


def test_concurrent_appends_have_one_chain(home):
    with ThreadPoolExecutor(max_workers=4) as pool:
        identities = list(pool.map(lambda number: audit.append("synthetic", str(number)), range(20)))
    assert sorted(identities) == list(range(1, 21))
    assert audit.integrity_info()["ok"]


def test_independent_processes_share_one_authenticated_chain(home):
    audit.append("baseline")
    script = "from linda_desktop.secure_audit import append; [append('process', str(i)) for i in range(4)]"
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    children = [subprocess.Popen([sys.executable, "-c", script], env=environment,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
    try:
        for child in children:
            output, errors = child.communicate(timeout=20)
            assert child.returncode == 0, errors.decode("utf-8", errors="replace")
        assert audit.integrity_info()["checkpoint"]["count"] == 13
        assert audit.integrity_info()["ok"]
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)


def test_complete_profile_rollback_is_explicitly_out_of_scope(home):
    assert audit.integrity_info()["limitations"] == ["same_user_or_admin", "complete_profile_rollback_or_deletion"]


def expired_prefix(home):
    audit.migrate_legacy([{"id": 1, "ts": 100.0, "action": "old", "detail": "EXPIRED_PRIVATE_PATH"},
                          {"id": 2, "ts": 101.0, "action": "old", "detail": "EXPIRED_PRIVATE_OTHER"}])
    audit.append("recent", "retained")
    return audit.integrity_info()["checkpoint"]


def test_retention_erases_payload_preserves_sequence_and_checkpoint(home):
    previous = expired_prefix(home)
    assert audit.retention(365) == 2
    rows = audit.list_entries()
    assert [r["id"] for r in rows] == [5, 4, 3]
    assert rows[0]["action"] == "audit_retention"
    info = audit.integrity_info()
    assert info["ok"] and info["checkpoint"]["epoch"] == 1
    assert info["checkpoint"]["first_id"] == 3
    assert info["checkpoint"]["previous_epoch_head"] == audit._checkpoint_summary(previous)
    assert "EXPIRED_PRIVATE" not in str(audit._read(home / "audit.ledger"))
    assert not (home / "audit.pending").exists()
    assert audit.append("after") == 6
    assert audit.retention(365) == 0
    assert audit.retention(0) == 0


@pytest.mark.parametrize("file", ["audit.ledger", "audit.checkpoint"])
def test_retention_tamper_detects_boundary_changes(home, file):
    expired_prefix(home)
    audit.retention(365)
    path = home / file
    data = audit._read(path)
    if file == "audit.ledger":
        data[0]["previous"] = audit._ZERO
    else:
        data["first_id"] = 1
    audit._write(path, data)
    assert not audit.integrity_info()["ok"]
    with pytest.raises(audit.AuditIntegrityError):
        audit.retention(365)


@pytest.mark.parametrize("failed_write", ["audit.ledger", "audit.checkpoint"])
def test_retention_crash_recovers_without_expired_payload(home, monkeypatch, failed_write):
    expired_prefix(home)
    write = audit._write
    with monkeypatch.context() as patch:
        def crash(path, value):
            if path.name == failed_write:
                raise OSError("retention crash")
            write(path, value)
        patch.setattr(audit, "_write", crash)
        with pytest.raises(OSError):
            audit.retention(365)
    assert audit.integrity_info()["ok"]
    assert "EXPIRED_PRIVATE" not in str(audit._read(home / "audit.ledger"))
    assert audit.integrity_info()["checkpoint"]["epoch"] == 1
    assert not (home / "audit.pending").exists()


def test_retention_entire_expired_ledger_keeps_next_sequence(home, monkeypatch):
    audit.append("private", "EXPIRED_PRIVATE_PATH")
    future = audit.time.time() + 400 * 86400
    with monkeypatch.context() as patch:
        patch.setattr(audit.time, "time", lambda: future)
        assert audit.retention(365) == 1
    assert [r["id"] for r in audit.list_entries()] == [2]
    assert audit.append("next") == 3
    assert audit.integrity_info()["ok"]


def test_repeated_retention_epochs_have_bounded_previous_head(home, monkeypatch):
    audit.append("first", "EXPIRED_PRIVATE")
    instant = audit.time.time()
    for epoch in range(1, 5):
        with monkeypatch.context() as patch:
            patch.setattr(audit.time, "time", lambda: instant + epoch * 400 * 86400)
            assert audit.retention(365) >= 1
            assert audit.integrity_info()["checkpoint"]["epoch"] == epoch
            assert "previous_epoch_head" not in audit.integrity_info()["checkpoint"]["previous_epoch_head"]
    assert "EXPIRED_PRIVATE" not in str(audit._read(home / "audit.ledger"))


def test_nonchronological_expiry_requires_explicit_intervention(home):
    now = audit.time.time()
    audit.migrate_legacy([{"id": 1, "ts": now, "action": "recent", "detail": "one"},
                          {"id": 2, "ts": 100.0, "action": "old", "detail": "older after recent"}])
    before = (home / "audit.ledger").read_bytes()
    with pytest.raises(audit.AuditIntegrityError, match="nonchronological"):
        audit.retention(365)
    assert (home / "audit.ledger").read_bytes() == before


def test_retention_checkpoint_commit_then_crash_finishes_cleanup(home, monkeypatch):
    expired_prefix(home)
    original = audit.Path.unlink
    with monkeypatch.context() as patch:
        def crash(path, *args, **kwargs):
            if path.name == "audit.pending":
                raise OSError("exit after retention checkpoint")
            return original(path, *args, **kwargs)
        patch.setattr(audit.Path, "unlink", crash)
        with pytest.raises(OSError):
            audit.retention(365)
    assert audit.integrity_info()["ok"]
    assert "EXPIRED_PRIVATE" not in str(audit._read(home / "audit.ledger"))
    assert not (home / "audit.pending").exists()
