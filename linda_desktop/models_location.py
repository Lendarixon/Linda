# -*- coding: utf-8 -*-
"""Выбор папки для моделей: проверка места, папочный диалог Windows, перенос уже скачанных моделей с прогрессом.

Модели (models/, onnx/, calibration/, manifest.json, staging/) лежат в config.models_root(): по умолчанию папка данных, либо выбранная пользователем
(страница установщика, первый запуск или «Настройки»). История, настройки и лицензия остаются в папке данных."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from . import config

ITEMS = ("models", "onnx", "calibration", "staging", "manifest.json", "manifest.json.sig")
NEED_GB = 6.0  # модели 2,9 ГБ + кэш ONNX 1,5 ГБ + запас на докачку обновления


def _roots_overlap(old: Path, new: Path) -> bool:
    """Return true when either resolved models root contains the other.

    Resolving before comparison also catches Windows junctions and symlink aliases.
    If resolution fails, fail closed: a move must never guess that deletion is safe.
    """
    try:
        old_root = Path(old).resolve(strict=False)
        new_root = Path(new).resolve(strict=False)
        return (old_root == new_root or old_root in new_root.parents
                or new_root in old_root.parents)
    except (OSError, RuntimeError, ValueError):
        return True


def free_gb(path: Path) -> float:
    p = Path(path)
    while not p.exists() and p.parent != p:
        p = p.parent
    try:
        return shutil.disk_usage(p).free / 2**30
    except OSError:
        return 0.0


def info() -> dict:
    st = config.models_location_state()
    root = Path(st["path"])
    has = (root / "models").is_dir() and any((root / "models").iterdir()) if (root / "models").exists() else False
    return {**st, "free_gb": round(free_gb(root), 1), "need_gb": NEED_GB, "has_models": has}


def validate(path: str) -> tuple[bool, str]:
    """(ok, key): key is a UI message key explaining a refusal."""
    try:
        p = Path(path)
    except Exception:  # noqa: BLE001
        return False, "loc_bad"
    if not p.is_absolute() or str(p).startswith("\\\\"):
        return False, "loc_bad"  # only a local absolute path (no network shares: slow and unreliable for 3 GB of weights)
    # Check against the active root before mkdir or the write probe. Overlapping
    # roots make the later source cleanup capable of deleting the new copy.
    if _roots_overlap(config.models_root(), p):
        return False, "loc_overlap"
    if len(str(p)) > 200:
        return False, "loc_long"
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".linda_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError:
        return False, "loc_noaccess"
    if free_gb(p) < NEED_GB:
        return False, "loc_space"
    return True, ""


def browse(initial: str = "") -> str | None:
    """Native Windows folder dialog (PowerShell + WinForms, STA). Returns the chosen folder or None."""
    if os.name != "nt":
        return None
    script = ("Add-Type -AssemblyName System.Windows.Forms;"
              "$d=New-Object System.Windows.Forms.FolderBrowserDialog;$d.ShowNewFolderButton=$true;"
              "$d.Description='Linda-Pro';"
              + ("$d.SelectedPath='%s';" % initial.replace("'", "''") if initial else "")
              + "$f=New-Object System.Windows.Forms.Form;$f.TopMost=$true;$f.ShowInTaskbar=$false;$f.WindowState='Minimized';$f.Show();"
              "if($d.ShowDialog($f) -eq 'OK'){[Console]::OutputEncoding=[Text.Encoding]::UTF8;Write-Output $d.SelectedPath};$f.Close()")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", script], capture_output=True, timeout=600, creationflags=0x08000000)
        text = out.stdout.decode("utf-8", errors="replace").strip()
        return text or None
    except Exception:  # noqa: BLE001
        return None


class MoveJob:
    """Copies models to the new folder with progress, then switches the pointer and removes the old copy."""

    def __init__(self) -> None:
        self.state = {"phase": "idle", "done": 0, "total": 0, "error": ""}
        self.lock = threading.Lock()

    def busy(self) -> bool:
        return self.state["phase"] in ("copying", "cleaning")

    def start(self, old: Path, new: Path, before=None) -> None:
        if _roots_overlap(old, new):
            raise ValueError("loc_overlap")
        with self.lock:
            if self.busy():
                raise RuntimeError("busy")
            self.state = {"phase": "copying", "done": 0, "total": 0, "error": ""}
        threading.Thread(target=self._run, args=(Path(old), Path(new), before), daemon=True).start()

    def _run(self, old: Path, new: Path, before) -> None:
        owned_parts: set[Path] = set()
        try:
            # Defense in depth for direct/background invocations: do this before
            # unloading the engine, creating destination directories, or copying.
            if _roots_overlap(old, new):
                raise ValueError("loc_overlap")
            if before:
                before()  # unload the engine: files must not be in use
            files: list[tuple[Path, Path]] = []
            for name in ITEMS:
                src = old / name
                if src.is_file():
                    files.append((src, new / name))
                elif src.is_dir():
                    files += [(f, new / name / f.relative_to(src)) for f in src.rglob("*") if f.is_file()]
            self.state["total"] = sum(f.stat().st_size for f, _ in files)
            for src, dst in files:
                dst.parent.mkdir(parents=True, exist_ok=True)
                fd, part_name = tempfile.mkstemp(prefix=dst.name + ".", suffix=".part", dir=str(dst.parent))
                part = Path(part_name)
                owned_parts.add(part)
                with os.fdopen(fd, "wb") as w, open(src, "rb") as r:
                    while chunk := r.read(8 << 20):
                        w.write(chunk)
                        self.state["done"] += len(chunk)
                os.replace(part, dst)
                owned_parts.discard(part)
            config.set_models_root(new)  # switch only after everything is copied
            self.state["phase"] = "cleaning"
            for name in ITEMS:
                src = old / name
                if src.is_dir():
                    shutil.rmtree(src, ignore_errors=True)
                elif src.is_file():
                    src.unlink(missing_ok=True)
            self.state["phase"] = "done"
        except Exception as e:  # noqa: BLE001
            self.state = {**self.state, "phase": "error", "error": "%s: %s" % (type(e).__name__, e)}
            # the old location stays valid: the pointer was not switched
            for f in owned_parts:
                try:
                    f.unlink()
                except OSError:
                    pass
