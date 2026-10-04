# -*- coding: utf-8 -*-
"""Constants and paths of the Linda-Pro desktop app."""
from __future__ import annotations

import os
from pathlib import Path

from . import __version__

APP_NAME = "Linda-Pro"
APP_VERSION = __version__
DEV_INSTALLER_ENABLED = False
DEV_APP_ID = 'B2701632-0C56-438F-B07E-9355CABF191A'

# Where the weights and the update manifest live. LINDA_BASE_URL overrides it (tests, mirrors).
HF_REPO = "Lindarixon/Linda-Pro"
BASE_URL = os.environ.get("LINDA_BASE_URL", f"https://huggingface.co/{HF_REPO}/resolve/main").rstrip("/")
MANIFEST_NAME = "latest.json"
SIGNATURE_NAME = "latest.json.sig"

# Ed25519 public key (base64, raw 32 bytes) that signs latest.json. The private key never leaves the owner's machine.
SIGNING_PUBKEY_B64 = os.environ.get("LINDA_PUBKEY_B64", "Om56X62V4ODc26e7wlbrqZrzEgZ47qmdLnZzcK/cTSk=")

# Polar (Merchant of Record). The organization id is not a secret; the validate/activate endpoints are public.
POLAR_API = os.environ.get("LINDA_POLAR_API", "https://api.polar.sh").rstrip("/")
POLAR_ORG_ID = os.environ.get("LINDA_POLAR_ORG_ID", "696a6525-f56d-4863-8e63-d8afc1fd3902")
BUY_URL_PERSONAL_TEAM = "https://buy.polar.sh/polar_cl_xbgd3gaCH2ZQIzNHmRAjyJiIUTNAHuRmE51zi1P8ywI"
BUY_URL_ORG = "https://buy.polar.sh/polar_cl_UznG2OPeM5diDZ1nCtxwRD1HW1pO3OZIu55DN07bCQe"
# Ed25519 public key that verifies complimentary ("gift") licence keys offline (LINDA-P-0001-..., LINDA-T-0001-...); a different key from the update-manifest key.
LICENSE_PUBKEY_B64 = os.environ.get("LINDA_LICENSE_PUBKEY_B64", "kK6CGNqIIJ49aYL1joTDHkO+SrJjCail5RqYHRRoMaY=")
CONTACT_EMAIL = "lindapro.support@proton.me"
REVALIDATE_DAYS = 7

UPDATE_CHECK_HOURS = 24
MAX_WORDS = None  # верхнего предела длины нет (раньше 20 000); окна расширяются сами, время растёт линейно
MIN_WORDS = 20


def package_family_name() -> str | None:
    """Ask Windows for actual package identity; an environment flag cannot fake it.

    None means an unpackaged process. Unexpected Windows API errors fail closed:
    silently treating a Store installation as EXE would enable the wrong updater.
    """
    if os.name != 'nt':
        return None
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    query = kernel.GetCurrentPackageFamilyName
    query.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
    query.restype = wintypes.LONG
    size = wintypes.UINT(0)
    result = query(ctypes.byref(size), None)
    if result == 15700:  # APPMODEL_ERROR_NO_PACKAGE
        return None
    if result != 122 or not 1 < size.value <= 512:  # ERROR_INSUFFICIENT_BUFFER
        raise RuntimeError(f'Cannot determine Windows package identity ({result})')
    value = ctypes.create_unicode_buffer(size.value)
    result = query(ctypes.byref(size), value)
    if result:
        raise RuntimeError(f'Cannot read Windows package identity ({result})')
    family = value.value
    if not family or any(c in family for c in ('/', '\\', ':')) or family in ('.', '..'):
        raise RuntimeError('Invalid Windows package family name')
    return family


def is_store_package() -> bool:
    """Packaged installations use Windows-managed app updates, including sideloads."""
    return package_family_name() is not None


def data_dir() -> Path:
    """Separate packaged LocalState from legacy EXE data; tests may override it."""
    env = os.environ.get("LINDA_HOME")
    if env:
        base = Path(env)
    else:
        local = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
        family = package_family_name()
        base = local / 'Packages' / family / 'LocalState' if family else local / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


# Корпоративные политики (только чтение, без сети): значения по умолчанию,
# поверх — %PROGRAMDATA%\Linda-Pro\enterprise.json (ставит админ), поверх —
# enterprise.json в папке данных, старые policy.json читаются так же.
ENTERPRISE_DEFAULTS = {
    "org_name": "", "disable_export": False, "disable_history": False,
    "require_license": False, "audit_retention_days": 365,
    "max_batch_files": 200, "allowed_dirs": [],
}


def program_data_dir() -> Path:
    r"""Общая папка политик: %PROGRAMDATA%\Linda-Pro (LINDA_PROGRAMDATA overrides, для тестов)."""
    env = os.environ.get("LINDA_PROGRAMDATA")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA") or r"C:\ProgramData") / APP_NAME
    return Path("/etc") / "linda-pro"


def _read_json(path: Path) -> dict:
    try:
        if path.is_file():
            d = __import__("json").loads(path.read_text(encoding="utf-8"))
            return d if isinstance(d, dict) else {}
    except Exception:  # noqa: BLE001 — битый файл политик не роняет приложение
        pass
    return {}


def enterprise() -> dict:
    """Итоговые корпоративные политики (дефолт + enterprise.json + старый policy.json)."""
    pol = dict(ENTERPRISE_DEFAULTS)
    # Политики администратора имеют приоритет: пользовательский файл не ослабляет запрет экспорта/лицензию.
    for p in (data_dir() / "policy.json", data_dir() / "enterprise.json",
              program_data_dir() / "policy.json", program_data_dir() / "enterprise.json"):
        for k, v in _read_json(p).items():
            if k in pol:
                pol[k] = v
    try:
        pol["max_batch_files"] = min(max(int(pol["max_batch_files"]), 1), 1000)
        pol["audit_retention_days"] = min(max(int(pol["audit_retention_days"]), 0), 3650)
    except (TypeError, ValueError):
        pol["max_batch_files"], pol["audit_retention_days"] = 200, 365
    return pol


def enterprise_allows_path(path: str) -> bool:
    """Разрешён ли каталог политикой allowed_dirs (пустой список — разрешено всё)."""
    allowed = enterprise().get("allowed_dirs") or []
    if not allowed:
        return True
    # Нормализация .. и junction: строковый префикс позволял выйти за разрешённую папку.
    try:
        target = Path(path).resolve()
        return any(target.is_relative_to(Path(a).resolve()) for a in allowed)
    except (OSError, ValueError, TypeError):
        return False


def resource_dir() -> Path:
    """Folder with web/ and bundled files (PyInstaller sets sys._MEIPASS)."""
    import sys

    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
