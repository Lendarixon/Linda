# -*- coding: utf-8 -*-
"""Downloads the Linda-Pro weights from Hugging Face into ./models (needs internet, ~2.9 GB; no login needed)."""
from pathlib import Path

from huggingface_hub import snapshot_download

here = Path(__file__).resolve().parent
snapshot_download(repo_id="Lindarixon/Linda-Pro", allow_patterns=["models/*", "models/**"], local_dir=str(here))
print("weights in", here / "models")
