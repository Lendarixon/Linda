# -*- coding: utf-8 -*-
"""Model download and updates.

The repository (Hugging Face) holds `latest.json` + `latest.json.sig`: a list of files (path, size, sha256), the weights version and
the installer of the application itself. The signature is Ed25519 over the exact bytes of `latest.json`; nothing is used before the
signature and every file hash check out. Downloads resume after an interruption. Only changed files are fetched on update."""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import shutil
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config

UA = {"User-Agent": f"Linda-Pro/{config.APP_VERSION}"}
CHUNK = 1 << 20


class UpdateError(Exception):
    pass


def vtuple(v: str) -> tuple:
    out = []
    for p in str(v).split("."):
        digits = "".join(c for c in p if c.isdigit())
        out.append(int(digits or 0))
    return tuple(out)


def _open(url: str, headers: dict | None = None, timeout: float = 30):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_bytes(url: str, timeout: float = 30, limit: int = 4_000_000) -> bytes:
    try:
        with _open(url, timeout=timeout) as r:
            data = r.read(limit + 1)
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise UpdateError("the model repository is not available without an access request (HTTP %d). The public release is not open yet; please try again later or contact support." % e.code) from e
        if e.code == 404:
            raise UpdateError("update information was not found on the server (HTTP 404); please try again later") from e
        raise UpdateError(f"update server error (HTTP {e.code})") from e
    except (urllib.error.URLError, OSError) as e:
        raise UpdateError(f"cannot reach the update server: {getattr(e, 'reason', e)}. Check your internet connection.") from e
    if len(data) > limit:
        raise UpdateError("response too large")
    return data


def verify_signature(raw: bytes, sig_b64: bytes, pubkey_b64: str | None = None) -> None:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(pubkey_b64 or config.SIGNING_PUBKEY_B64))
        pub.verify(base64.b64decode(sig_b64.strip()), raw)
    except (InvalidSignature, ValueError, TypeError) as e:
        raise UpdateError("update manifest signature is invalid") from e


def get_manifest(base_url: str | None = None) -> tuple[dict, bytes]:
    base = (base_url or config.BASE_URL).rstrip("/")
    raw = fetch_bytes(f"{base}/{config.MANIFEST_NAME}")
    sig = fetch_bytes(f"{base}/{config.SIGNATURE_NAME}", limit=4096)
    verify_signature(raw, sig)
    try:
        m = json.loads(raw.decode("utf-8"))
        assert m["schema"] == 1 and isinstance(m["files"], list) and m["version"]
        for f in m["files"]:
            assert isinstance(f["path"], str) and isinstance(f["size"], int) and len(f["sha256"]) == 64
            p = Path(f["path"])
            assert not p.is_absolute() and ".." not in p.parts  # no path traversal
    except Exception as e:  # noqa: BLE001
        raise UpdateError("update manifest is malformed") from e
    return m, raw


def installed_manifest() -> dict | None:
    p = config.data_dir() / "manifest.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception:  # noqa: BLE001
        return None


def installed_version() -> str | None:
    m = installed_manifest()
    return m["version"] if m else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(CHUNK):
            h.update(chunk)
    return h.hexdigest()


def files_to_fetch(manifest: dict, root: Path | None = None) -> list[dict]:
    """Entries that are missing or differ from the manifest. Files listed in the installed manifest with the same hash and size are trusted."""
    root = root or config.data_dir()
    old = {f["path"]: f for f in (installed_manifest() or {}).get("files", [])}
    todo = []
    for f in manifest["files"]:
        p = root / f["path"]
        ok = p.is_file() and p.stat().st_size == f["size"]
        if ok and not (f["path"] in old and old[f["path"]]["sha256"] == f["sha256"]):
            ok = sha256_file(p) == f["sha256"]
        if not ok:
            todo.append(f)
    return todo


def is_complete(manifest: dict | None = None, root: Path | None = None) -> bool:
    m = manifest or installed_manifest()
    if not m:
        return False
    root = root or config.data_dir()
    return all((root / f["path"]).is_file() and (root / f["path"]).stat().st_size == f["size"] for f in m["files"])


class Job:
    """Background download with progress; cancel() stops it between chunks (partial files are kept for resuming)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state = {"phase": "idle", "file": "", "done": 0, "total": 0, "error": "", "speed": 0.0, "version": ""}
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_done = None

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.state)

    def _set(self, **kw) -> None:
        with self.lock:
            self.state.update(kw)

    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def cancel(self) -> None:
        self._cancel.set()

    def start(self, manifest: dict, raw: bytes, root: Path | None = None, base_url: str | None = None) -> bool:
        if self.running():
            return False
        self._cancel.clear()
        self._set(phase="checking", file="", done=0, total=0, error="", speed=0.0, version=manifest["version"])
        self._thread = threading.Thread(target=self._run, args=(manifest, raw, root or config.data_dir(), (base_url or config.BASE_URL).rstrip("/")), daemon=True)
        self._thread.start()
        return True

    def _run(self, manifest: dict, raw: bytes, root: Path, base: str) -> None:
        try:
            todo = files_to_fetch(manifest, root)
            self._set(total=sum(f["size"] for f in todo), done=0, phase="downloading")
            done_before = 0
            t0 = time.time()
            for f in todo:
                self._set(file=f["path"])
                self._download(f, root, base, done_before, t0)
                done_before += f["size"]
            self._set(phase="finishing", file="")
            self._cleanup(manifest, root)
            (root / "manifest.json").write_bytes(raw)
            self._set(phase="done", done=self.state["total"])
            if self.on_done:
                self.on_done(manifest)
        except _Cancelled:
            self._set(phase="cancelled")
        except Exception as e:  # noqa: BLE001
            self._set(phase="error", error=str(e) if isinstance(e, UpdateError) else f"{type(e).__name__}: {e}")

    def _download(self, f: dict, root: Path, base: str, done_before: int, t0: float) -> None:
        dest = root / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        url = f"{base}/{urllib.parse.quote(f['path'])}"
        for attempt in range(4):
            try:
                have = part.stat().st_size if part.exists() else 0
                if have > f["size"]:
                    part.unlink()
                    have = 0
                h = hashlib.sha256()
                if have:
                    with open(part, "rb") as pf:
                        while chunk := pf.read(CHUNK):
                            h.update(chunk)
                if have < f["size"]:
                    r = _open(url, {"Range": f"bytes={have}-"} if have else None, timeout=30)
                    with r:
                        if have and getattr(r, "status", 200) != 206:  # server ignored Range: restart this file
                            have, h = 0, hashlib.sha256()
                        with open(part, "ab" if have else "wb") as out:
                            got = have
                            while True:
                                if self._cancel.is_set():
                                    raise _Cancelled()
                                chunk = r.read(CHUNK)
                                if not chunk:
                                    break
                                out.write(chunk)
                                h.update(chunk)
                                got += len(chunk)
                                el = max(time.time() - t0, 0.5)
                                self._set(done=done_before + got, speed=(done_before + got) / el)
                if part.stat().st_size != f["size"]:
                    raise ConnectionError(f"incomplete download of {f['path']}")
                if h.hexdigest() != f["sha256"]:
                    part.unlink(missing_ok=True)
                    raise UpdateError(f"checksum mismatch for {f['path']}")
                os.replace(part, dest)
                return
            except (urllib.error.URLError, OSError, ConnectionError, http.client.HTTPException) as e:
                if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404):
                    raise UpdateError(f"server refused {f['path']} (HTTP {e.code})") from e
                if attempt == 3:
                    raise UpdateError(f"network error while downloading {f['path']}: {e}") from e
                time.sleep(2 + attempt * 3)

    @staticmethod
    def _cleanup(manifest: dict, root: Path) -> None:
        """Remove files of older versions inside the managed folders (models/, calibration/)."""
        keep = {Path(f["path"]).as_posix() for f in manifest["files"]}
        for top in sorted({Path(f["path"]).parts[0] for f in manifest["files"]}):
            base = root / top
            if not base.is_dir():
                continue
            for p in sorted(base.rglob("*"), reverse=True):
                rel = p.relative_to(root).as_posix()
                if p.is_file() and rel not in keep:
                    p.unlink(missing_ok=True)
                elif p.is_dir() and not any(p.iterdir()):
                    p.rmdir()


class _Cancelled(Exception):
    pass


def download_installer(info: dict, progress=None) -> Path:
    """Downloads the application installer named in the manifest (https only) into a temp folder and verifies its sha256."""
    url = info["url"]
    if not url.startswith("https://") and not os.environ.get("LINDA_ALLOW_HTTP"):
        raise UpdateError("installer url must be https")
    dest = Path(tempfile.mkdtemp(prefix="linda_upd_")) / "Linda-Setup.exe"
    h = hashlib.sha256()
    with _open(url, timeout=60) as r, open(dest, "wb") as out:
        got = 0
        while chunk := r.read(CHUNK):
            out.write(chunk)
            h.update(chunk)
            got += len(chunk)
            if progress:
                progress(got, int(info.get("size") or 0))
    if h.hexdigest() != info["sha256"]:
        shutil.rmtree(dest.parent, ignore_errors=True)
        raise UpdateError("installer checksum mismatch")
    return dest


def update_status(manifest: dict) -> dict:
    """Compare a verified manifest with what is installed and with this app."""
    inst = installed_version()
    out = {"remote_version": manifest["version"], "installed_version": inst, "notes": manifest.get("notes", ""),
           "weights_update": bool(inst) and vtuple(manifest["version"]) > vtuple(inst), "weights_missing": not is_complete(),
           "app_required": vtuple(manifest.get("min_app", "0")) > vtuple(config.APP_VERSION), "app_new": False, "installer": None}
    ins = manifest.get("installer")
    if ins and vtuple(ins.get("version", "0")) > vtuple(config.APP_VERSION):
        out["app_new"] = True
        out["installer"] = {"version": ins["version"], "size": ins.get("size", 0)}
    if out["weights_update"] or out["weights_missing"]:
        out["bytes_to_download"] = sum(f["size"] for f in files_to_fetch(manifest))
    return out
