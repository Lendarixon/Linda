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
            "licensed": licensing.public_state()["licensed"], "job": job_snapshot()}


def job_snapshot() -> dict:
    with _pack_lock:
        return dict(_pack_job)


def _set_job(**kw) -> None:
    with _pack_lock:
        _pack_job.update(kw)


def _poll_sizes(stop, variants):
    """Пока качается base, показываем живые байты: сумма файлов растёт, итог — оценка."""
    from . import humanize_pack  # noqa: PLC0415

    while not stop.is_set():
        try:
            done = 0
            total = 0
            for v in variants:
                d = humanize_pack.variant_dirs(v)
                sz = sum(p.stat().st_size for p in d["root"].rglob("*") if p.is_file()) if d["root"].is_dir() else 0
                done += sz
                total += max(humanize_pack.estimated_bytes(v), sz)
            _set_job(done=done, total=total)
        except Exception:
            pass
        stop.wait(1.0)


_VALID_INSTALLER_PACKS = ("trace", "humanizer-lite", "humanizer-full")


def maybe_install_installer_packs() -> dict:
    """Download licensed packs selected in the installer (`installer_choice.json['packs']`).

    Runs once in the background after startup licence activation/revalidation.
    Leaves the choice intact when unlicensed so a later activation can trigger it.
    """
    from . import humanize_pack, licensing, trace_pack  # noqa: PLC0415

    choice_path = config.data_dir() / "installer_choice.json"
    try:
        choice = json.loads(choice_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "none"}
    if not isinstance(choice, dict):
        return {"status": "none"}
    raw_packs = choice.get("packs")
    if not isinstance(raw_packs, list) or not raw_packs:
        return {"status": "none"}
    wanted = [p for p in dict.fromkeys(str(x).strip().lower() for x in raw_packs) if p in _VALID_INSTALLER_PACKS]
    if not wanted:
        return {"status": "none"}
    if not licensing.public_state().get("licensed"):
        return {"status": "unlicensed", "packs": wanted}

    missing = []
    for p in wanted:
        if p == "trace" and not trace_pack.installed():
            missing.append(p)
        elif p == "humanizer-lite" and not humanize_pack.installed("lite"):
            missing.append(p)
        elif p == "humanizer-full" and not humanize_pack.installed("full"):
            missing.append(p)

    queue = []
    if "trace" in missing:
        queue.append("trace")
    if "humanizer-lite" in missing and "humanizer-full" in missing:
        queue.append("humanizer-all")
    else:
        for p in ("humanizer-lite", "humanizer-full"):
            if p in missing:
                queue.append(p)

    installed_now, failed = [], []
    for item in queue:
        if not try_start(item):
            failed.append(item)
            continue
        try:
            download(item)
            installed_now.append(item)
        except Exception:  # noqa: BLE001
            failed.append(item)

    if not failed:
        try:
            choice["packs"] = []
            choice_path.write_text(json.dumps(choice, indent=1), encoding="utf-8")
        except OSError:
            pass
    return {"status": "ok" if not failed else "partial", "ran": installed_now, "failed": failed}


def try_start(pack: str) -> bool:
    """Atomically mark the job as running; False when another download is active.

    Callers must run packs.download(pack) right after a True result so the
    check-and-start in the API handler is race-free.
    """
    with _pack_lock:
        if _pack_job["phase"] == "running":
            return False
        _pack_job.update(phase="running", pack=pack, done=0, total=100, error="")
        return True


def download(pack: str) -> dict:
    """Start (synchronously, caller threads it) downloading a pack. Returns final state."""
    from . import humanize_pack  # noqa: PLC0415

    with _pack_lock:
        if _pack_job["phase"] == "running" and _pack_job["pack"] != pack:
            raise RuntimeError("another pack download is running")
        _pack_job.update(phase="running", pack=pack, done=0, total=100, error="")
    stop = None
    poll = None
    try:
        if pack == "humanizer-lite":
            if not humanize_pack.installed("lite"):
                _set_job(total=humanize_pack.estimated_bytes("lite"))
                stop, poll = _start_poll(["lite"])
                humanize_pack.download_base("lite")
            else:
                humanize_pack.download_base("lite")
        elif pack == "humanizer-full":
            if not humanize_pack.installed("full"):
                _set_job(total=humanize_pack.estimated_bytes("full"))
                stop, poll = _start_poll(["full"])
                humanize_pack.download_base("full")
            else:
                humanize_pack.download_base("full")
        elif pack == "humanizer-all":
            _set_job(total=humanize_pack.estimated_bytes("lite") + humanize_pack.estimated_bytes("full"))
            stop, poll = _start_poll(["lite", "full"])
            humanize_pack.download_base("lite")
            humanize_pack.download_base("full")
        elif pack == "trace":
            from . import trace_pack  # noqa: PLC0415

            if not trace_pack.installed():
                raise RuntimeError("trace payload missing")
        else:
            raise ValueError("unknown pack")
        with _pack_lock:
            _pack_job.update(phase="ready", done=_pack_job.get("total", 100))
    except Exception as e:  # noqa: BLE001
        with _pack_lock:
            _pack_job.update(phase="error", error=str(e)[:300])
        raise
    finally:
        try:
            if stop is not None:
                stop.set()
            if poll is not None:
                poll.join(timeout=2.0)
        except Exception:
            pass
    return job_snapshot()


def _start_poll(variants):
    import threading as _th

    stop = _th.Event()
    poll = _th.Thread(target=_poll_sizes, args=(stop, variants), daemon=True)
    poll.start()
    return stop, poll
