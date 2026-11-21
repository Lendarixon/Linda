# -*- coding: utf-8 -*-
"""Forensic authorship (Linda Trace) embedded as a licensed pack.

The engine files live in linda_desktop/trace/ (synced from the Linda Trace repo,
outlier_engine 2.0.1 / authorship_engine 1.1.0). They use top-level imports, so the
folder is added to sys.path on first use. Nothing is loaded until ensure() runs,
and every public function requires a licence (any tier, including subscription).
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

from . import config


def _trace_dir() -> Path:
    """Engine payload dir: next to this file in dev; in the bundle either the
    frozen temp dir (_MEIPASS, one-file) or _internal next to the exe (one-dir/disk)."""
    cands: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(Path(meipass) / "linda_desktop" / "trace")
    if getattr(sys, "frozen", False):
        cands.append(Path(sys.executable).parent / "_internal" / "linda_desktop" / "trace")
    cands.append(Path(__file__).resolve().parent / "trace")
    for c in cands:
        if (c / "char_ngrams_model.json").is_file():
            return c
    return cands[0] if cands else Path(__file__).resolve().parent / "trace"


ENGINE_VERSION = "2.0.1"
_ALIAS_MODULES = ("core", "feature_labels", "input_quality", "projection_2d", "runtime_manifest",
                  "trace_config", "trace_updater", "stylometric_engine", "outlier_engine",
                  "authorship_engine", "report_builder")
_lock = threading.Lock()
_loaded = False


def pack_dir() -> Path:
    """User-writable Trace data (settings, updates). Engine payload ships with the app."""
    p = config.data_dir() / "trace"
    p.mkdir(parents=True, exist_ok=True)
    return p


def installed() -> bool:
    d = _trace_dir()
    if not (d / "char_ngrams_model.json").is_file():
        return False
    if (d / "outlier_engine.py").is_file():
        return True
    # упакованное приложение: код движка внутри exe (PYZ), на диске только данные
    return bool(getattr(sys, "frozen", False))


def version() -> str:
    return ENGINE_VERSION


def _alias_frozen() -> None:
    """Frozen fallback when the payload is only inside the PYZ (no files on disk):
    import as linda_desktop.trace.* and expose the short names the engines expect."""
    import importlib  # noqa: PLC0415

    for short in _ALIAS_MODULES:
        if short in sys.modules:
            continue
        full = "linda_desktop.trace." + short
        try:
            mod = sys.modules.get(full) or importlib.import_module(full)
        except ImportError:
            continue
        sys.modules.setdefault(short, mod)
    try:
        vendor_pkg = importlib.import_module("linda_desktop.trace.vendor")
        sys.modules.setdefault("vendor", vendor_pkg)
    except ImportError:
        pass


def _patch_paths() -> None:
    """Point file-based lookups (__file__-relative) at the real payload dir."""
    d = _trace_dir()
    try:
        import stylometric_engine as _se  # noqa: PLC0415

        _se.MODEL_PATH = d / "char_ngrams_model.json"
    except Exception:  # noqa: BLE001
        pass
    try:
        import trace_config as _tc  # noqa: PLC0415

        _tc.BASE_DIR = d
    except Exception:  # noqa: BLE001
        pass


def ensure() -> None:
    """Make the engine importable (idempotent, thread-safe). Raises if payload missing."""
    global _loaded
    with _lock:
        if _loaded:
            return
        if not installed():
            raise RuntimeError("trace pack is not installed")
        os.environ.setdefault("FORENSIC_DATA_ROOT", str(pack_dir()))
        d = _trace_dir()
        if (d / "outlier_engine.py").is_file():
            # Dev tree or bundled data files: plain imports, exactly like the Trace repo.
            if str(d) not in sys.path:
                sys.path.insert(0, str(d))
        else:
            _alias_frozen()
        import outlier_engine  # noqa: PLC0415,F401
        import authorship_engine  # noqa: PLC0415,F401

        _patch_paths()
        _loaded = True


def analyze_corpus(documents: list, language: str = "ru", target_id: str | None = None) -> dict:
    """Relative stylistic ranking inside the given corpus. Not proof of authorship."""
    ensure()
    import outlier_engine  # noqa: PLC0415

    docs = [{"id": str(d.get("id") or i), "title": str(d.get("title") or d.get("id") or i),
             "text": str(d.get("text") or "")} for i, d in enumerate(documents or [])]
    from . import task_cancel
    task_cancel.check()
    return outlier_engine.analyze_corpus(docs, language=language or "ru", target_id=target_id,
                                        progress=lambda *args:task_cancel.check())


def analyze_authorship(references: list, documents: list, language: str = "ru",
                       guard: bool = True, deeptrace: bool = False) -> dict:
    ensure()
    import authorship_engine  # noqa: PLC0415

    refs = [{"author": str(r.get("author") or "?"), "title": str(r.get("title") or ""),
             "text": str(r.get("text") or "")} for r in (references or [])]
    docs = [{"id": str(d.get("id") or i), "title": str(d.get("title") or d.get("id") or i),
             "text": str(d.get("text") or "")} for i, d in enumerate(documents or [])]
    return authorship_engine.analyze_authorship(refs, docs, language=language or "ru",
                                                enable_false_match_guard=bool(guard),
                                                enable_deeptrace=False)  # DeepTrace weights are a separate pack; never claim ready


def html_report(analysis: dict, documents: list, selected_id: str | None = None) -> str:
    ensure()
    import report_builder  # noqa: PLC0415

    return report_builder.render_report(analysis, documents, selected_id=selected_id)


def status() -> dict:
    d = _trace_dir()
    return {"installed": installed(), "version": version() if installed() else None,
            "size": sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) if installed() else 0}
