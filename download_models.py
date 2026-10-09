# -*- coding: utf-8 -*-
"""Downloads the Linda-Pro weights from Hugging Face into ./models and ./calibration (needs internet; no login needed).
    python download_models.py                 # Linda-Pro (the full ensemble, ~2.9 GB)
    python download_models.py --set lite      # Linda-Pro Lite (small and fast, ~0.6 GB, any CPU)
    python download_models.py --set both"""
import argparse
from pathlib import Path

from huggingface_hub import snapshot_download

ap = argparse.ArgumentParser()
ap.add_argument("--set", choices=["pro", "lite", "both"], default="pro")
a = ap.parse_args()
here = Path(__file__).resolve().parent
if a.set in ("pro", "both"):
    snapshot_download(repo_id="Lindarixon/Linda-Pro", local_dir=str(here),
                      allow_patterns=["calibration/routing.json", "models/essay_dhi_131_*/*", "models/multi_dhi_131_*/*", "models/stylo_d/*"])
if a.set in ("lite", "both"):
    snapshot_download(repo_id="Lindarixon/Linda-Pro-Lite", local_dir=str(here),
                      allow_patterns=["calibration/routing.json", "models/linda_speed_131/*", "models/linda_speed_131/**/*", "models/stylo_l/*", "models/stylo_d/*"])
print("weights in", here / "models")
