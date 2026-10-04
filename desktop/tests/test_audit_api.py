"""Protected audit API integration using synthetic temporary Windows profiles."""
import time

import pytest
from fastapi.testclient import TestClient

from linda_desktop import config, history, protected_storage, secure_audit
from linda_desktop.app import create_app

TOKEN = "synthetic-audit-api-token"


@pytest.fixture
def context(tmp_path, monkeypatch):
    root = tmp_path / "synthetic-profile"
    root.mkdir()
    monkeypatch.setattr(config, "data_dir", lambda: root)
    monkeypatch.setattr(config, "enterprise", lambda: {"audit_retention_days": 365})
    client = TestClient(create_app(object(), token=TOKEN), headers={"x-linda-token": TOKEN})
    return root, client


def _snapshot(root):
    return {path.name: path.read_bytes() for path in root.iterdir() if path.is_file() and path.name != "audit.lock"}


def test_get_migrates_protected_legacy_and_applies_retention(context):
    root, client = context
    now = time.time()
    with history._db() as db:
        db.execute("INSERT INTO audit (ts, action, detail) VALUES (?,?,?)",
                   (now - 400 * 86400, "old_document", "EXPIRED_SYNTHETIC_PRIVATE_PATH"))
        db.execute("INSERT INTO audit (ts, action, detail) VALUES (?,?,?)",
                   (now, "current_document", "retained synthetic detail"))
    assert (root / "history.db").read_bytes().startswith(protected_storage.MAGIC)
    response = client.get("/api/audit")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["integrity"]["ok"]
    assert "old_document" not in [row["action"] for row in data["items"]]
    assert "current_document" in [row["action"] for row in data["items"]]
    assert "audit_retention" in [row["action"] for row in data["items"]]
    assert data["integrity"]["checkpoint"]["epoch"] == 1
    assert "EXPIRED_SYNTHETIC_PRIVATE_PATH" not in str(secure_audit._read(root / "audit.ledger"))
    with history._db() as db:
        assert db.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 0
    # SQLite DELETE alone can leave legacy detail in freelist/page remnants;
    # migration must not retain expired audit payload in the protected snapshot.
    decoded_history = protected_storage.unprotect((root / "history.db").read_bytes(), "history-db")
    assert b"EXPIRED_SYNTHETIC_PRIVATE_PATH" not in decoded_history
    repeat = client.get("/api/audit")
    assert repeat.status_code == 200
    assert [row["id"] for row in repeat.json()["items"]] == [row["id"] for row in data["items"]]
    filtered = client.get("/api/audit", params={"action": "current_document", "limit": 1})
    assert filtered.status_code == 200
    assert len(filtered.json()["items"]) == 1
    assert filtered.json()["items"][0]["legacy"] is True


@pytest.mark.parametrize("damage", ["edit", "truncate", "missing_checkpoint"])
def test_tampered_audit_returns_409_without_reset(context, damage):
    root, client = context
    history.audit("one", "synthetic detail one")
    history.audit("two", "synthetic detail two")
    if damage == "missing_checkpoint":
        (root / "audit.checkpoint").unlink()
    else:
        rows = secure_audit._read(root / "audit.ledger")
        if damage == "edit":
            rows[0]["detail"] = "modified"
        else:
            rows.pop()
        secure_audit._write(root / "audit.ledger", rows)
    before = _snapshot(root)
    response = client.get("/api/audit")
    assert response.status_code == 409, response.text
    assert response.json().get("detail")
    assert _snapshot(root) == before


def test_delete_forbidden_preserves_entries_and_files(context):
    root, client = context
    history.audit("one", "synthetic detail")
    entries = history.audit_list()
    before = _snapshot(root)
    response = client.delete("/api/audit")
    assert response.status_code == 403
    assert history.audit_list() == entries
    assert _snapshot(root) == before


def test_nonchronological_retention_returns_409_without_reset(context):
    root, client = context
    with history._db() as db:
        db.execute("INSERT INTO audit (ts,action,detail) VALUES (?,?,?)", (time.time(), "recent", "synthetic"))
        db.execute("INSERT INTO audit (ts,action,detail) VALUES (?,?,?)", (100.0, "old", "nonchronological"))
    history._migrate_audit()
    before = _snapshot(root)
    response = client.get("/api/audit")
    assert response.status_code == 409, response.text
    assert _snapshot(root) == before


def test_unauthenticated_access_cannot_read_or_reset(context):
    root, client = context
    history.audit("one", "private synthetic detail")
    before = _snapshot(root)
    assert client.get("/api/audit", headers={"x-linda-token": "wrong"}).status_code == 403
    assert client.delete("/api/audit", headers={"x-linda-token": "wrong"}).status_code == 403
    assert _snapshot(root) == before
