"""Encrypted, tamper-evident local audit with a recoverable commit journal.

DPAPI and an independent checkpoint protect against accidental corruption and
offline editing without the Windows user's credentials. They cannot defend
against that user/admin, deletion of the entire profile, or full-profile rollback.
Legacy events are explicitly unverified before their import boundary.
"""
from __future__ import annotations

import contextlib
import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path

from . import config

_LOCK = threading.RLock()
_ZERO = "0" * 64
_PURPOSE = "linda.audit.v1"


class AuditIntegrityError(RuntimeError):
    """Audit cannot be trusted; do not silently reset it or append new events."""


def _encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _protect(raw):
    from .protected_storage import protect
    return protect(raw, purpose=_PURPOSE)


def _unprotect(raw):
    from .protected_storage import unprotect
    return unprotect(raw, purpose=_PURPOSE)


def _atomic(path: Path, raw: bytes):
    tmp = path.with_name(path.name + ".tmp")
    try:
        with tmp.open("wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def _write(path, value):
    _atomic(path, _protect(_encode(value)))


def _read(path):
    try:
        return json.loads(_unprotect(path.read_bytes()).decode("utf-8"))
    except Exception as exc:
        raise AuditIntegrityError("Audit storage missing, damaged or inaccessible") from exc


@contextlib.contextmanager
def _locked():
    with _LOCK:
        root = config.data_dir()
        root.mkdir(parents=True, exist_ok=True)
        with (root / "audit.lock").open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            try:
                yield root
            finally:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _head(rows):
    compaction = next((r["compaction"] for r in reversed(rows) if "compaction" in r), None)
    return {"count": len(rows), "mac": rows[-1]["mac"] if rows else _ZERO,
            "first_id": rows[0]["id"] if rows else 1,
            "first_previous": rows[0]["previous"] if rows else _ZERO,
            "last_id": rows[-1]["id"] if rows else 0,
            "epoch": compaction["epoch"] if compaction else 0,
            "previous_epoch_head": compaction["previous_head"] if compaction else None,
            "removed_total": compaction["removed_total"] if compaction else 0}


def _checkpoint_summary(head):
    # Keep a bounded previous-epoch anchor, not a recursively nested history.
    return {k: v for k, v in head.items() if k != "previous_epoch_head"}


def _verify(rows, key):
    if not isinstance(rows, list):
        raise AuditIntegrityError("Invalid audit ledger")
    previous = rows[0].get("previous", _ZERO) if rows else _ZERO
    first_id = rows[0].get("id", 1) if rows else 1
    if not isinstance(first_id, int) or first_id < 1:
        raise AuditIntegrityError("Invalid audit sequence boundary")
    for index, row in enumerate(rows, first_id):
        try:
            required = {"id", "ts", "action", "detail", "legacy", "previous"}
            if not required.issubset(row):
                raise ValueError("missing record field")
            payload = {k: v for k, v in row.items() if k != "mac"}
            expected = hmac.new(key, _encode(payload), hashlib.sha256).hexdigest()
            if row["id"] != index or row["previous"] != previous or not hmac.compare_digest(row["mac"], expected):
                raise ValueError("chain mismatch")
            previous = row["mac"]
        except Exception as exc:
            raise AuditIntegrityError("Audit record order or authentication mismatch") from exc


def _recover(root, key):
    pending = root / "audit.pending"
    if not pending.exists():
        return
    transaction = _read(pending)
    try:
        rows, base = transaction["rows"], transaction["base"]
        _verify(rows, key)
        target = _head(rows)
        operation = transaction.get("operation", "append")
        if operation == "append":
            if base != _head(rows[:base["count"]]) or base["count"] >= target["count"]:
                raise ValueError("invalid transaction prefix")
        elif operation == "retention":
            marker = rows[-1]
            compaction = marker.get("compaction", {})
            if (compaction.get("previous_head") != _checkpoint_summary(base) or compaction.get("epoch") != base["epoch"] + 1
                    or marker["id"] != base["last_id"] + 1
                    or marker["previous"] != base["mac"]
                    or target["first_id"] <= base["first_id"]):
                raise ValueError("invalid retention boundary")
        else:
            raise ValueError("unknown journal operation")
        current = _read(root / "audit.checkpoint")
        ledger = _read(root / "audit.ledger")
        _verify(ledger, key)
        ledger_head = _head(ledger)
        if current not in (base, target) or ledger_head not in (base, target):
            raise ValueError("unexpected checkpoint or ledger")
        if current == target and ledger_head != target:
            raise ValueError("ledger rollback after commit")
        if operation == "retention" and ledger_head == base:
            if rows[:-1] != ledger[target["first_id"] - base["first_id"]:]:
                raise ValueError("retention changed surviving records")
        _write(root / "audit.ledger", rows)
        _write(root / "audit.checkpoint", target)
        pending.unlink()
    except AuditIntegrityError:
        raise
    except Exception as exc:
        raise AuditIntegrityError("Audit recovery journal is inconsistent") from exc


def _load(root):
    names = ("audit.key", "audit.ledger", "audit.checkpoint")
    present = [(root / name).exists() for name in names]
    if not any(present) and not (root / "audit.pending").exists():
        _write(root / "audit.key", {"key": os.urandom(32).hex()})
        _write(root / "audit.ledger", [])
        _write(root / "audit.checkpoint", _head([]))
    elif not all(present):
        raise AuditIntegrityError("Audit files removed or initialization interrupted")
    try:
        key = bytes.fromhex(_read(root / "audit.key")["key"])
        if len(key) != 32:
            raise ValueError("invalid key")
    except Exception as exc:
        raise AuditIntegrityError("Audit key damaged or inaccessible") from exc
    _recover(root, key)
    rows = _read(root / "audit.ledger")
    _verify(rows, key)
    checkpoint = _read(root / "audit.checkpoint")
    # Upgrade the original non-compacted v1 checkpoint only after its original
    # chain and head have been authenticated. Never infer a compacted boundary.
    if set(checkpoint) == {"count", "mac"} and (not rows or (rows[0]["id"] == 1 and rows[0]["previous"] == _ZERO)):
        if checkpoint == {"count": len(rows), "mac": _head(rows)["mac"]}:
            checkpoint = _head(rows)
            _write(root / "audit.checkpoint", checkpoint)
    if checkpoint != _head(rows):
        raise AuditIntegrityError("Audit checkpoint mismatch: truncation or rollback")
    return rows, key


def _commit(root, previous_rows, rows, operation="append"):
    # Journal is flushed before either durable file changes. A crash at any later
    # step completes this authenticated transaction at the next read/append.
    _write(root / "audit.pending", {"base": _head(previous_rows), "rows": rows, "operation": operation})
    _write(root / "audit.ledger", rows)
    _write(root / "audit.checkpoint", _head(rows))
    (root / "audit.pending").unlink()


def _record(rows, key, action, detail, ts=None, legacy=False, compaction=None, identity=None, previous=None):
    row = {"id": (rows[-1]["id"] + 1 if rows else 1) if identity is None else identity,
           "ts": time.time() if ts is None else float(ts),
           "action": str(action)[:60], "detail": str(detail)[:2000],
           "legacy": bool(legacy), "previous": _head(rows)["mac"] if previous is None else previous}
    if compaction is not None:
        row["compaction"] = compaction
    row["mac"] = hmac.new(key, _encode(row), hashlib.sha256).hexdigest()
    rows.append(row)
    return row["id"]


def append(action: str, detail: str = "") -> int:
    with _locked() as root:
        rows, key = _load(root)
        old = list(rows)
        identity = _record(rows, key, action, detail)
        _commit(root, old, rows)
        return identity


def retention(days: int) -> int:
    """Remove an expired contiguous prefix, preserving a signed epoch boundary.

    Payloads removed by policy can no longer be independently verified. Sequence
    IDs never reset. Ciphertext backups / filesystem remnants are not secure erase.
    Zero days means keep forever. If historical/clock-rollback timestamps put an
    expired entry after an unexpired entry, fail closed for explicit intervention
    instead of silently violating the configured retention policy.
    """
    days = int(days)
    if days <= 0:
        return 0
    with _locked() as root:
        rows, key = _load(root)
        cutoff = time.time() - days * 86400
        count = 0
        for row in rows:
            if row["ts"] >= cutoff:
                break
            count += 1
        if any(row["ts"] < cutoff for row in rows[count:]):
            raise AuditIntegrityError("Audit retention blocked by nonchronological timestamps; explicit intervention required")
        if count == 0:
            return 0
        previous = _head(rows)
        retained = list(rows[count:])
        compaction = {"epoch": previous["epoch"] + 1, "previous_head": _checkpoint_summary(previous),
                      "removed": count, "removed_total": previous["removed_total"] + count,
                      "retained_from_id": retained[0]["id"] if retained else previous["last_id"] + 1,
                      "cutoff": cutoff}
        _record(retained, key, "audit_retention", "expired_prefix_removed=%d; days=%d" % (count, days),
                compaction=compaction, identity=previous["last_id"] + 1, previous=previous["mac"])
        _commit(root, rows, retained, operation="retention")
        return count


def list_entries(action: str = "", limit: int = 200, offset: int = 0) -> list[dict]:
    with _locked() as root:
        rows, _ = _load(root)
        selected = [r for r in reversed(rows) if not action or r["action"] == action]
        start = max(0, int(offset))
        return [dict(r) for r in selected[start:start + min(1000, max(1, int(limit)))]]


def integrity_info() -> dict:
    try:
        with _locked() as root:
            rows, _ = _load(root)
            return {"ok": True, "version": 2, "checkpoint": _head(rows),
                    "legacy_entries": sum(r["legacy"] for r in rows),
                    "scope": "local_current_user", "external_anchor": False,
                    "limitations": ["same_user_or_admin", "complete_profile_rollback_or_deletion"]}
    except AuditIntegrityError as exc:
        return {"ok": False, "error": str(exc), "scope": "local_current_user", "external_anchor": False}


def migrate_legacy(legacy_rows) -> int:
    """Import once on an empty ledger; caller removes old table only after success.

    Original IDs are retained in detail, because new IDs describe chain order.
    Existing nonempty ledger rejects migration, except an identical prior import.
    """
    source = sorted([dict(row) for row in legacy_rows], key=lambda r: int(r["id"]))
    fingerprint = hashlib.sha256(_encode(source)).hexdigest()
    marker = "legacy_sha256=" + fingerprint
    with _locked() as root:
        rows, key = _load(root)
        if any(r["action"] == "audit_legacy_import" and r["detail"] == marker for r in rows):
            return 0
        if rows:
            raise AuditIntegrityError("Legacy import requires an empty ledger")
        if not source:
            return 0
        old = list(rows)
        for entry in source:
            _record(rows, key, entry["action"], "legacy_id=%s; %s" % (entry["id"], entry["detail"]), entry["ts"], True)
        _record(rows, key, "audit_legacy_import", marker)
        _commit(root, old, rows)
        return len(source)
