# -*- coding: utf-8 -*-
"""Constants and paths of the Linda-Pro desktop app."""
from __future__ import annotations

import os
from pathlib import Path

from . import __version__

APP_NAME = "Linda-Pro"
APP_VERSION = __version__

# Where the weights and the update manifest live. LINDA_BASE_URL overrides it (tests, mirrors).
HF_REPO = "Lindarixon/Linda-Pro"
BASE_URL = os.environ.get("LINDA_BASE_URL", f"https://huggingface.co/{HF_REPO}/resolve/main").rstrip("/")
MANIFEST_NAME = "latest.json"
SIGNATURE_NAME = "latest.json.sig"

# Ed25519 public key (base64, raw 32 bytes) that signs latest.json. The private key never leaves the owner's machine.
SIGNING_PUBKEY_B64 = os.environ.get("LINDA_PUBKEY_B64", "Om56X62V4ODc26e7wlbrqZrzEgZ47qmdLnZzcK/cTSk=")

# Polar (Merchant of Record). The organization id is not a secret; the validate/activate endpoints are public.
POLAR_API = os.environ.get("LINDA_POLAR_API", "https://api.polar.sh").rstrip("/")
POLAR_ORG_ID = os.environ.get("LINDA_POLAR_ORG_ID", "")
BUY_URL_PERSONAL_TEAM = "https://buy.polar.sh/polar_cl_xbgd3gaCH2ZQIzNHmRAjyJiIUTNAHuRmE51zi1P8ywI"
BUY_URL_ORG = "https://buy.polar.sh/polar_cl_UznG2OPeM5diDZ1nCtxwRD1HW1pO3OZIu55DN07bCQe"
CONTACT_EMAIL = "ninjagovlad@gmail.com"
REVALIDATE_DAYS = 7

UPDATE_CHECK_HOURS = 24
MAX_WORDS = 20000
MIN_WORDS = 20


def data_dir() -> Path:
    """%LOCALAPPDATA%\\Linda-Pro (LINDA_HOME overrides, for tests)."""
    env = os.environ.get("LINDA_HOME")
    base = Path(env) if env else Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share") / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def resource_dir() -> Path:
    """Folder with web/ and bundled files (PyInstaller sets sys._MEIPASS)."""
    import sys

    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
