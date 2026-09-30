# -*- coding: utf-8 -*-
"""Скачивает веса Linda-Pro с Hugging Face в ./models (нужен интернет, ~2.7 ГБ)."""
from pathlib import Path

from huggingface_hub import snapshot_download

here = Path(__file__).resolve().parent
snapshot_download(repo_id="Lindarixon/Linda-Pro", allow_patterns=["models/*", "models/**"], local_dir=str(here))
print("weights in", here / "models")
