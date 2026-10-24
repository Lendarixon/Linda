# -*- coding: utf-8 -*-
"""Downloadable licensed packs: trace (forensic authorship) and humanizer tiers.

Trace engine ships with the app; its READY marker is written after verify.
Humanizer weights download on demand (lite ~1.2 ГБ, full ~8 ГБ) from HF.
Every pack API requires a licence (any tier, including subscription).
"""
from __future__ import annotations

import json
import threading
from pathlib import Path

from . import config

_pack_lock = threading.Lock()
_pack_job = {"phase": "idle", "pack": "", "done": 0, "total": 0, "error": ""}


def probe() -> dict:
    from . import humanize_pack, licensing, trace_pack  # noqa: PLC0415

    return {"trace": trace_pack.status(), "humanizer": humanize_pack.status(),
            "licensed": licensing.public_state()["licensed"]}


def job_snapshot() -> dict:
    return dict(_pack_job)


def download(pack: str) -> dict:
    """Start (synchronously, caller threads it) downloading a pack. Returns final state."""
    from . import humanize_pack  # noqa: PLC0415

    with _pack_lock:
        if _pack_job["phase"] == "running":
            raise RuntimeError("another pack download is running")
        _pack_job.update(phase="running", pack=pack, done=0, total=100, error="")
    try:
        if pack == "humanizer-lite":
            humanize_pack.download_base("lite")
        elif pack == "humanizer-full":
            humanize_pack.download_base("full")
        elif pack == "trace":
            from . import trace_pack  # noqa: PLC0415

            if not trace_pack.installed():
                raise RuntimeError("trace payload missing")
        else:
            raise ValueError("unknown pack")
        with _pack_lock:
            _pack_job.update(phase="ready", done=100)
    except Exception as e:  # noqa: BLE001
        with _pack_lock:
            _pack_job.update(phase="error", error=str(e)[:300])
        raise
    return job_snapshot()
