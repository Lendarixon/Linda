# -*- coding: utf-8 -*-
"""Licence key (Polar). The app is free for personal non-commercial use; a key unlocks commercial use and hides the notice.
Nothing is blocked without a key. Network use: one activation call when the key is entered, then a validation call at most once
every REVALIDATE_DAYS days; offline the cached state is kept. No texts or personal data are sent (only the key and a random device label)."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid

from . import config

UA = {"User-Agent": f"Linda-Pro/{config.APP_VERSION}", "Content-Type": "application/json"}


class LicenseError(Exception):
    pass


def _path():
    return config.data_dir() / "license.json"


def load() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8")) if _path().exists() else {}
    except Exception:  # noqa: BLE001
        return {}


def _save(d: dict) -> None:
    _path().write_text(json.dumps(d, indent=1), encoding="utf-8")


def _post(path: str, body: dict, timeout: float = 20) -> tuple[int, dict]:
    req = urllib.request.Request(f"{config.POLAR_API}{path}", data=json.dumps(body).encode("utf-8"), headers=UA, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode("utf-8") or "{}")
        except Exception:  # noqa: BLE001
            return e.code, {}
    except (urllib.error.URLError, OSError) as e:
        raise LicenseError("cannot reach the licence server; check your internet connection") from e


def _detail(j: dict) -> str:
    d = j.get("detail")
    if isinstance(d, str):
        return d
    if isinstance(d, list) and d:
        return str(d[0].get("msg", d[0]))
    return j.get("error_description") or j.get("error") or ""


def tier_of(limit_activations) -> str:
    n = limit_activations or 0
    return "personal" if n and n <= 3 else "team" if n and n <= 20 else "organization"


def _mask(key: str) -> str:
    return key[:6] + "..." + key[-4:] if len(key) > 12 else "..."


_GIFT_RE = re.compile(r"^LINDA-([PT])-(\d{4})-([A-Z2-7-]{100,125})$")
GIFT_TIERS = {"P": "personal", "T": "team"}


def verify_gift(key: str, pubkey_b64: str | None = None) -> dict | None:
    """Offline check of a complimentary key: Ed25519 signature over "linda-gift|<P|T>|<number>". Returns {"tier", "id", "key"} or None."""
    k = re.sub(r"\s+", "", key or "").upper()
    m = _GIFT_RE.match(k)
    if not m:
        return None
    code, num, sig = m.groups()
    raw = sig.replace("-", "")
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        sigb = base64.b32decode(raw + "=" * (-len(raw) % 8))
        Ed25519PublicKey.from_public_bytes(base64.b64decode(pubkey_b64 or config.LICENSE_PUBKEY_B64)).verify(sigb, f"linda-gift|{code}|{num}".encode())
    except (InvalidSignature, ValueError, TypeError):
        return None
    return {"tier": GIFT_TIERS[code], "id": f"{code}-{num}", "key": k}


def apply_revocations(ids: list) -> None:
    """Called with the `revoked` list of the signed update manifest: a revoked complimentary key stops being licensed."""
    st = load()
    if st.get("kind") == "gift" and st.get("gift_id") in set(ids or []) and st.get("status") != "revoked":
        st["status"] = "revoked"
        _save(st)


def activate(key: str) -> dict:
    key = (key or "").strip()
    if not key:
        raise LicenseError("enter your licence key")
    g = verify_gift(key)
    if g:  # complimentary key: verified offline, no network needed
        st = {"key": g["key"], "kind": "gift", "gift_id": g["id"], "activated_at": int(time.time()), "last_validated": int(time.time()), "status": "granted", "tier": g["tier"]}
        _save(st)
        return public_state(st)
    if re.match(r"^\s*LINDA-[PT]-\d{4}-", key, re.I):
        raise LicenseError("this key is not valid; check that it was copied completely (it is long)")
    if not config.POLAR_ORG_ID:
        raise LicenseError("licensing is not configured in this build yet")
    label = "Windows-" + uuid.uuid4().hex[:6]
    mid = machine_id()
    code, j = _post("/v1/customer-portal/license-keys/activate", {"key": key, "organization_id": config.POLAR_ORG_ID, "label": label, "conditions": {"machine": mid}})
    if code not in (200, 201):
        msg = _detail(j)
        if code == 403:
            raise LicenseError("this key has reached its device limit; free a device in your Polar customer portal or write to " + config.CONTACT_EMAIL)
        if code in (404, 422):
            raise LicenseError("licence key not found; check that you copied it completely")
        raise LicenseError(f"licence server answered {code}" + (f": {msg}" if msg else ""))
    lk = j.get("license_key") or {}
    if lk.get("status") not in (None, "granted"):
        raise LicenseError(f"this key is {lk.get('status')}")
    st = {"key": key, "activation_id": j.get("id"), "label": label, "machine": mid, "activated_at": int(time.time()), "last_validated": int(time.time()),
          "status": "granted", "limit_activations": lk.get("limit_activations"), "expires_at": lk.get("expires_at"),
          "tier": tier_of(lk.get("limit_activations"))}
    _save(st)
    return public_state(st)


def machine_id() -> str:
    """Anonymous id of THIS computer: a salted hash of the Windows MachineGuid (a random file in the data folder where that is not available). The raw guid never leaves the PC."""
    guid = None
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k:
                guid = str(winreg.QueryValueEx(k, "MachineGuid")[0])
        except OSError:
            guid = None
    if not guid:
        p = config.data_dir() / "machine.id"
        if not p.exists():
            p.write_text(uuid.uuid4().hex, encoding="utf-8")
        guid = p.read_text(encoding="utf-8").strip()
    return hashlib.sha256(("linda-pro|" + guid).encode()).hexdigest()[:24]


def deactivate_local() -> None:
    """Remove the key from this computer and, if online, free its device slot at the licence server (so the key can be entered on another computer)."""
    st = load()
    if st.get("key") and st.get("kind") != "gift" and st.get("activation_id") and config.POLAR_ORG_ID:
        try:
            _post("/v1/customer-portal/license-keys/deactivate", {"key": st["key"], "organization_id": config.POLAR_ORG_ID, "activation_id": st["activation_id"]}, timeout=10)
        except LicenseError:
            pass  # offline: the slot can be freed later in the Polar customer portal
    try:
        _path().unlink()
    except FileNotFoundError:
        pass


def revalidate(force: bool = False) -> dict:
    """Check the saved key online if it has not been checked for REVALIDATE_DAYS days. Network errors keep the cached state."""
    st = load()
    if not st.get("key") or st.get("kind") == "gift":  # complimentary keys are verified offline; revocation comes with the signed manifest
        return public_state(st)
    if not force and time.time() - st.get("last_validated", 0) < config.REVALIDATE_DAYS * 86400:
        return public_state(st)
    if not config.POLAR_ORG_ID:
        return public_state(st)
    try:
        code, j = _post("/v1/customer-portal/license-keys/validate", {"key": st["key"], "organization_id": config.POLAR_ORG_ID, "activation_id": st.get("activation_id"),
                                                                                    "conditions": {"machine": st.get("machine") or machine_id()}})
    except LicenseError:
        return public_state(st)
    if code == 200:
        st["status"] = j.get("status", "granted")
        st["expires_at"] = j.get("expires_at")
        st["last_validated"] = int(time.time())
    elif code in (403, 404):  # revoked, deleted or the activation was removed
        st["status"] = "revoked"
        st["last_validated"] = int(time.time())
    _save(st)
    return public_state(st)


def public_state(st: dict | None = None) -> dict:
    st = load() if st is None else st
    active = bool(st.get("key")) and st.get("status") == "granted"
    status = st.get("status") or "none"
    if active and st.get("kind") != "gift" and st.get("machine") and st["machine"] != machine_id():
        active, status = False, "other_machine"  # the licence file was copied from another computer
    exp = st.get("expires_at")
    if active and exp:
        try:
            from datetime import datetime, timezone

            if datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < datetime.now(timezone.utc):
                active = False
        except Exception:  # noqa: BLE001
            pass
    return {"licensed": active, "kind": st.get("kind", "purchase"), "tier": st.get("tier") if active else None, "key_hint": _mask(st["key"]) if st.get("key") else "",
            "status": status, "configured": bool(config.POLAR_ORG_ID)}
