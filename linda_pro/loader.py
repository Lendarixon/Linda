# -*- coding: utf-8 -*-
"""load_detector(): the detector that matches the weights on disk.

Version 1.3.x weights (calibration/routing.json with kind "merged" and the folders it names) give a RoutedLindaPro (English, Polish and Russian,
one decision rule per language). Without them the older single-language LindaPro (1.1 weights) is used."""
from __future__ import annotations

import json
from pathlib import Path

from .core import PKG_ROOT, LindaPro


def _routing(root: Path) -> dict | None:
    p = root / "calibration" / "routing.json"
    if not p.is_file():
        return None
    try:
        table = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if table.get("kind") != "merged":
        return None
    dirs = table.get("voice_dirs") or {}
    if not dirs or not all((root / "models" / d).is_dir() for d in dirs.values()):
        return None
    return table


def load_detectors(root: str | Path | None = None, device: str | None = None) -> dict:
    """{"sensitive": detector, "precise": detector}; both share one model pool, so the weights are loaded once."""
    root = Path(root) if root else PKG_ROOT
    table = _routing(root)
    if table is None:
        return {"sensitive": LindaPro(mode="sensitive", device=device), "precise": LindaPro(mode="precise", device=device)}
    from .routed import ModelPool, RoutedLindaPro
    from .voters import FastSeqCls, StyloVoter

    dirs = table["voice_dirs"]
    models = root / "models"

    def make_voice(key: str):
        if key == "stylo_d":
            return StyloVoter(models / dirs["stylo_d"])
        return FastSeqCls(models / dirs[key], device=device)

    pool = ModelPool(make_voice, {"essay": 870, "multi": 560, "stylo": 0}, budget_mb=2600)
    table_path = root / "calibration" / "routing.json"
    return {m: RoutedLindaPro(table_path, make_voice, mode=m, pool=pool) for m in ("sensitive", "precise")}


def load_detector(mode: str = "sensitive", root: str | Path | None = None, device: str | None = None):
    return load_detectors(root, device)[mode]
