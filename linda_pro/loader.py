# -*- coding: utf-8 -*-
"""load_detector(): the detector that matches the weights on disk.

Version 1.3.x weights (calibration/routing.json with kind "merged") give a RoutedLindaPro for English, Polish and Russian. Two sets exist:
  * Linda-Pro (tier "full"): the large ensemble (folders essay_dhi_* and multi_dhi_*), best accuracy, a graphics card helps;
  * Linda-Pro Lite (tier "speed"): one small model (folder linda_speed_*) plus stylometry, runs on any CPU in seconds.
With both installed the full tier is used unless tier="lite" is asked for; with only one installed that one is used. Without 1.3.x weights the older LindaPro (1.1) is used."""
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
    return table if table.get("kind") == "merged" else None


def available_tiers(root: Path, table: dict) -> dict:
    dirs, models = table.get("voice_dirs") or {}, root / "models"
    full = all(k in dirs and (models / dirs[k]).is_dir() for k in ("essay_m", "multi_m", "stylo_d"))
    lite = "speed_s" in dirs and (models / dirs["speed_s"] / "model.onnx").is_file() and all("speed" in table["languages"][lg]["tiers"] for lg in table["languages"])
    return {"full": full, "lite": lite}


def load_detectors(root: str | Path | None = None, device: str | None = None, tier: str | None = None) -> dict:
    """{"sensitive": detector, "precise": detector}; both share one model pool, so the weights are loaded once. tier: None (best installed), "full" or "lite"."""
    root = Path(root) if root else PKG_ROOT
    table = _routing(root)
    have = available_tiers(root, table) if table else {"full": False, "lite": False}
    if not (have["full"] or have["lite"]):
        return {"sensitive": LindaPro(mode="sensitive", device=device), "precise": LindaPro(mode="precise", device=device)}
    use_lite = have["lite"] and (tier == "lite" or not have["full"])
    if tier == "full" and not have["full"]:
        raise FileNotFoundError("Linda-Pro (full) weights are not installed; run download_models.py or use tier='lite'")
    from .routed import ModelPool, RoutedLindaPro
    from .voters import FastSeqCls, SpeedOnnx, StyloVoter

    dirs = table["voice_dirs"]
    models = root / "models"

    def make_voice(key: str):
        if key.startswith("stylo_l_"):
            return StyloVoter(models / dirs[key], key[-2:])
        if key.startswith("stylo"):
            return StyloVoter(models / dirs[key])
        if key.startswith("speed_s"):
            return SpeedOnnx(models / dirs[key])
        return FastSeqCls(models / dirs[key], device=device)

    pool = ModelPool(make_voice, {"essay": 870, "multi": 560, "stylo": 0, "speed": 560}, budget_mb=2600)
    table_path = root / "calibration" / "routing.json"
    return {m: RoutedLindaPro(table_path, make_voice, mode=m, pool=pool, tier="speed" if use_lite else None) for m in ("sensitive", "precise")}


def load_detector(mode: str = "sensitive", root: str | Path | None = None, device: str | None = None, tier: str | None = None):
    return load_detectors(root, device, tier)[mode]
