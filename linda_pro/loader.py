# -*- coding: utf-8 -*-
"""load_detector(): the detector that matches the weights on disk.

Routed weights, 1.3.x and later (calibration/routing.json with kind "merged") give a RoutedLindaPro for English, Polish and Russian. Two sets exist:
  * Linda-Pro (tier "full"): the large ensemble (folders essay_dhi_* and multi_dhi_*, plus essay_l14m50 / multi_l14m50 for Polish and Russian since 1.4.1), best accuracy, a graphics card helps;
  * Linda-Pro Lite (tier "speed"): one small model (folder linda_speed_*) plus stylometry, runs on any CPU in seconds.
With both installed the full tier is used unless tier="lite" is asked for; with only one installed that one is used. Without routed weights the older LindaPro (1.1) is used if its weights are on disk; otherwise FileNotFoundError says how to download."""
from __future__ import annotations

import json
from pathlib import Path

from .core import MODEL_SUBDIRS, PKG_ROOT, LindaPro


def _routing(root: Path) -> dict | None:
    p = root / "calibration" / "routing.json"
    if not p.is_file():
        return None
    try:
        table = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return table if table.get("kind") == "merged" else None


def _voice_installed(models: Path, dirs: dict, key: str) -> bool:
    if key not in dirs:
        return False
    d = models / dirs[key]
    return (d / "model.onnx").is_file() if key.startswith("speed") else d.is_dir() and any(d.iterdir())


def available_tiers(root: Path, table: dict) -> dict:
    """A tier counts as installed only when every voice that any language's tier needs is on disk
    (routing 1.4.1+ uses separate PL/RU voices, essay_l14 / multi_l14, beside the English ones)."""
    dirs, models, langs = table.get("voice_dirs") or {}, root / "models", table.get("languages") or {}

    def ok(name: str) -> bool:
        return bool(langs) and all(name in v["tiers"] and all(_voice_installed(models, dirs, k) for k in v["tiers"][name]["voters"]) for v in langs.values())

    return {"full": ok("full"), "lite": ok("speed")}


TIERS = ("auto", "full", "lite")
MODES = ("sensitive", "precise")


def installed_tiers(root: str | Path | None = None) -> dict:
    """{"full": bool, "lite": bool} for the 1.3.x weights under root (default: the package checkout)."""
    root = Path(root) if root else PKG_ROOT
    table = _routing(root)
    return available_tiers(root, table) if table else {"full": False, "lite": False}


def _no_weights_message(root: Path) -> str:
    return (f"no Linda-Pro weights found under {root / 'models'}; run `python download_models.py` (Linda-Pro, ~5.8 GB) "
            "or `python download_models.py --set lite` (Linda-Pro Lite, ~0.3 GB)")


def load_detectors(root: str | Path | None = None, device: str | None = None, tier: str | None = None) -> dict:
    """{"sensitive": detector, "precise": detector}; both share one model pool, so the weights are loaded once.
    tier: None or "auto" (best installed: full, else lite), "full" or "lite". Asking for a tier that is not installed raises FileNotFoundError."""
    if tier not in (None, *TIERS):
        raise ValueError(f"tier must be one of {', '.join(TIERS)}, got {tier!r}")
    tier = None if tier == "auto" else tier
    root = Path(root) if root else PKG_ROOT
    table = _routing(root)
    have = available_tiers(root, table) if table else {"full": False, "lite": False}
    if tier == "full" and not have["full"]:
        raise FileNotFoundError("Linda-Pro (full) weights are not installed; run `python download_models.py`, or use Lite (--lite / tier='lite')")
    if tier == "lite" and not have["lite"]:
        raise FileNotFoundError("Linda-Pro Lite weights are not installed; run `python download_models.py --set lite`, or use the full set (--tier full / tier='full')")
    if not (have["full"] or have["lite"]):
        legacy = [root / "calibration" / "calibration_windowed_v6.json"] + [root / "models" / d for d in MODEL_SUBDIRS.values()]
        if not all(p.exists() for p in legacy):
            raise FileNotFoundError(_no_weights_message(root))
        return {m: LindaPro(calibration=legacy[0], models_dir=root / "models", mode=m, device=device) for m in MODES}
    use_lite = have["lite"] and (tier == "lite" or not have["full"])
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
    """One detector; see load_detectors for tier. mode: "sensitive" (default) or "precise"."""
    if mode not in MODES:
        raise ValueError("mode must be 'sensitive' or 'precise'")
    return load_detectors(root, device, tier)[mode]
