# -*- coding: utf-8 -*-
"""Downloads the Linda-Pro weights from Hugging Face into ./models and ./calibration (needs internet; no login needed).
    python download_models.py                 # Linda-Pro (the full ensemble: English + Polish/Russian voices, ~5.8 GB)
    python download_models.py --set lite      # Linda-Pro Lite (small and fast, ~0.3 GB, any CPU)
    python download_models.py --set both
Then: python -m linda_pro file.txt [--lite]"""
import argparse
import shutil
from pathlib import Path

from huggingface_hub import snapshot_download

PRO_REPO, LITE_REPO = "Lindarixon/Linda-Pro", "Lindarixon/Linda-Pro-Lite"
# routing.json: full tiers only; routing.with_lite.json: the same full tiers plus the Lite ("speed") tiers.
TABLES = ["calibration/routing.json", "calibration/routing.with_lite.json"]
PRO_MODELS = ["models/essay_dhi_131_*/*", "models/multi_dhi_131_*/*", "models/essay_l14m50/*", "models/multi_l14m50/*", "models/stylo_d/*"]
LITE_MODELS = ["models/linda_speed_131/*", "models/linda_speed_131/**/*", "models/stylo_l/*", "models/stylo_d/*"]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Download Linda-Pro weights from Hugging Face")
    ap.add_argument("--set", choices=["pro", "lite", "both"], default="pro")
    a = ap.parse_args(argv)
    here = Path(__file__).resolve().parent
    # Routing tables always come from the main repository, so Lite and full share one calibration (the Lite repository's table is older).
    snapshot_download(repo_id=PRO_REPO, local_dir=str(here), allow_patterns=TABLES + (PRO_MODELS if a.set in ("pro", "both") else []))
    if a.set in ("lite", "both"):
        snapshot_download(repo_id=LITE_REPO, local_dir=str(here), allow_patterns=LITE_MODELS)
    cal = here / "calibration"
    if (here / "models" / "linda_speed_131" / "model.onnx").is_file():
        shutil.copyfile(cal / "routing.with_lite.json", cal / "routing.json")  # enable the Lite tiers (full tiers unchanged)
    print("weights in", here / "models")


if __name__ == "__main__":
    main()
