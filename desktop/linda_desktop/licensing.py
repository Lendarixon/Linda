# -*- coding: utf-8 -*-
"""Licence key (Polar). The app is free for personal non-commercial use; a key unlocks commercial use and hides the notice.
Nothing is blocked without a key. Network use: one activation call when the key is entered, then a validation call at most once
every REVALIDATE_DAYS days; offline the cached state is kept. No texts or personal data are sent (only the key and a random device label)."""
from __future__ import annotations

import json
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


def activate(key: str) -> dict:
    key = (key or "").strip()
    if not key:
        raise LicenseError("enter your licence key")
    if not config.POLAR_ORG_ID:
        raise LicenseError("licensing is not configured in this build yet")
    label = "Windows-" + uuid.uuid4().hex[:6]
    code, j = _post("/v1/customer-portal/license-keys/activate", {"key": key, "organization_id": config.POLAR_ORG_ID, "label": label})
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
    st = {"key": key, "activation_id": j.get("id"), "label": label, "activated_at": int(time.time()), "last_validated": int(time.time()),
          "status": "granted", "limit_activations": lk.get("limit_activations"), "expires_at": lk.get("expires_at"),
          "tier": tier_of(lk.get("limit_activations"))}
    _save(st)
    return public_state(st)


def deactivate_local() -> None:
    """Forget the key on this computer (the device slot is freed in the Polar customer portal)."""
    try:
        _path().unlink()
    except FileNotFoundError:
        pass


def revalidate(force: bool = False) -> dict:
    """Check the saved key online if it has not been checked for REVALIDATE_DAYS days. Network errors keep the cached state."""
    st = load()
    if not st.get("key"):
        return public_state(st)
    if not force and time.time() - st.get("last_validated", 0) < config.REVALIDATE_DAYS * 86400:
        return public_state(st)
    if not config.POLAR_ORG_ID:
        return public_state(st)
    try:
        code, j = _post("/v1/customer-portal/license-keys/validate", {"key": st["key"], "organization_id": config.POLAR_ORG_ID, "activation_id": st.get("activation_id")})
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
    exp = st.get("expires_at")
    if active and exp:
        try:
            from datetime import datetime, timezone

            if datetime.fromisoformat(str(exp).replace("Z", "+00:00")) < datetime.now(timezone.utc):
                active = False
        except Exception:  # noqa: BLE001
            pass
    return {"licensed": active, "tier": st.get("tier") if active else None, "key_hint": _mask(st["key"]) if st.get("key") else "",
            "status": st.get("status") or "none", "configured": bool(config.POLAR_ORG_ID)}
