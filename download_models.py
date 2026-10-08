# -*- coding: utf-8 -*-
"""Downloads the Linda-Pro 1.3.1 weights and routing table from Hugging Face into ./models and ./calibration (needs internet, ~2.9 GB; no login needed)."""
from pathlib import Path

from huggingface_hub import snapshot_download

here = Path(__file__).resolve().parent
snapshot_download(repo_id="Lindarixon/Linda-Pro", local_dir=str(here),
                  allow_patterns=["calibration/routing.json", "models/essay_dhi_131_*/*", "models/multi_dhi_131_*/*", "models/stylo_d/*"])
print("weights in", here / "models")
