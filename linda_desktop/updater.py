# -*- coding: utf-8 -*-
"""Model download and updates.

The repository (Hugging Face) holds `latest.json` + `latest.json.sig`: a list of files (path, size, sha256), the weights version and
the installer of the application itself. The signature is Ed25519 over the exact bytes of `latest.json`; nothing is used before the
signature and every file hash check out. Downloads resume after an interruption. Only changed files are fetched on update."""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import http.client
import json
import logging
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
CHUNK = 1 << 20  # 1 MiB read/write chunk
OK_SUFFIX = ".ok"  # marker beside a verified file: "<sha256> <size>" - skips re-hashing on later passes
MAX_PARALLEL = 4  # concurrent file downloads in Job._run
OPTIONAL_PATHS = ("calibration/routing.with_lite.json",)
SKIPPED_OPTIONAL_FILE = "skipped_optional.json"
_LOG = logging.getLogger("linda.updater")


def _is_optional_entry(f: dict) -> bool:
    if f.get("optional"):
        return True
    rel = Path(str(f.get("path") or "")).as_posix().casefold()
    return rel in OPTIONAL_PATHS or rel.endswith("/routing.with_lite.json") or rel == "routing.with_lite.json"


def _read_skipped_optional(root: Path) -> dict[str, str]:
    p = root / SKIPPED_OPTIONAL_FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
        return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _write_skipped_optional(root: Path, skipped: dict[str, str]) -> None:
    p = root / SKIPPED_OPTIONAL_FILE
    if not skipped:
        p.unlink(missing_ok=True)
        return
    tmp = p.with_name(p.name + ".new")
    tmp.write_text(json.dumps(skipped, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def _is_skipped_optional(f: dict, skipped_map: dict[str, str]) -> bool:
    return _is_optional_entry(f) and skipped_map.get(f["path"]) == f["sha256"]


class UpdateError(Exception):
    pass


@contextmanager
def _apply_guard(lock, cancel):
    acquired = False
    try:
        if lock is not None:
            while not lock.acquire(timeout=0.2):
                if cancel.is_set():
                    raise _Cancelled()
            acquired = True
        if cancel.is_set():
            raise _Cancelled()
        yield
    finally:
        if acquired:
            lock.release()


def vtuple(v: str) -> tuple:
    out = []
    for p in str(v).split("."):
        digits = "".join(c for c in p if c.isdigit())
        out.append(int(digits or 0))
    return tuple(out)


def _open(url: str, headers: dict | None = None, timeout: float = 30):
    parsed = urllib.parse.urlparse(url)
    if os.environ.get('LINDA_DEV') == '1' and parsed.scheme == 'http' and parsed.hostname not in ('127.0.0.1', 'localhost', '::1'):
        raise UpdateError('Dev HTTP update source must be loopback')
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
        validate_manifest(m)
    except Exception as e:  # noqa: BLE001
        raise UpdateError("update manifest is malformed") from e
    m['_signature'] = sig.decode('ascii').strip()
    return effective(m), raw


def validate_manifest(m: dict) -> None:
    """Проверяем и локальный staging: подпись сетевого ответа не заменяет проверку путей."""
    if m.get('schema') != 1 or not isinstance(m.get('files'), list) or not m.get('version'):
        raise UpdateError('update manifest is malformed')
    seen = set()
    for f in m['files']:
        rel, size, digest = f.get('path'), f.get('size'), f.get('sha256')
        if not isinstance(rel, str) or '\\' in rel or ':' in rel or '\x00' in rel:
            raise UpdateError('update manifest is malformed')
        p = Path(rel)
        if p.is_absolute() or '..' in p.parts or len(p.parts) < 2 or p.parts[0] not in ('models', 'calibration', 'onnx'):
            raise UpdateError('update manifest is malformed')
        key = p.as_posix().casefold()
        if key in seen or type(size) is not int or size < 0 or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdefABCDEF' for c in digest):
            raise UpdateError('update manifest is malformed')
        seen.add(key)


def _safe_path(root: Path, rel: str) -> Path:
    path = root / rel
    if not path.resolve().is_relative_to(root.resolve()):
        raise UpdateError('update path leaves managed directory')
    return path


SETS = ('pro', 'lite')


def _valid_sets(value) -> list[str] | None:
    if isinstance(value, list) and value and all(x in SETS for x in value):
        return [x for x in SETS if x in value]
    return None


def _raw_installed_version() -> str | None:
    p = config.models_root() / 'manifest.json'
    try:
        m = json.loads(p.read_text(encoding='utf-8')) if p.exists() else None
        if isinstance(m, dict) and isinstance(m.get('version'), str):
            return m['version']
    except Exception:
        pass
    return None


def _reused_sets(choice: dict) -> list[str] | None:
    reuse = choice.get('reuse_models')
    if not reuse:
        return None
    if isinstance(reuse, dict):
        ver = reuse.get('version') or choice.get('reuse_version')
        sets = _valid_sets(reuse.get('sets')) or _valid_sets(choice.get('reuse_sets')) or _valid_sets(choice.get('model_sets'))
    else:
        ver = choice.get('reuse_version')
        sets = _valid_sets(choice.get('reuse_sets')) or _valid_sets(choice.get('model_sets'))
    if not ver or not sets:
        return None
    if _raw_installed_version() == ver:
        return sets
    return None


def selected_sets() -> list[str]:
    """The sets this computer keeps: the user's choice (settings.json), else the installer's choice (honoring reuse_models when versions match), else what is already on the disk, else Linda-Pro."""
    try:
        got = _valid_sets(json.loads((config.data_dir() / 'settings.json').read_text(encoding='utf-8')).get('model_sets'))
        if got:
            return got
    except Exception:
        pass
    try:
        choice = json.loads((config.data_dir() / 'installer_choice.json').read_text(encoding='utf-8'))
        if isinstance(choice, dict):
            reused = _reused_sets(choice)
            if reused:
                return reused
            got = _valid_sets(choice.get('model_sets'))
            if got:
                return got
    except Exception:
        pass
    root = config.models_root() / 'models'
    present = []
    try:
        if any(root.glob('essay_dhi*')) or any(root.glob('linda_essay*')):
            present.append('pro')
        if any(root.glob('linda_speed*')):
            present.append('lite')
    except OSError:
        pass
    return present or ['pro']


def wanted(entry: dict, sets: list[str] | None = None) -> bool:
    s = entry.get('set', 'shared')
    return s == 'shared' or s in (sets or selected_sets())


def effective(m: dict) -> dict:
    """The manifest as this computer sees it: only the files of the selected sets (all_files keeps the whole list for sizes)."""
    out = dict(m)
    out['all_files'] = m.get('all_files', m['files'])
    sel = selected_sets()
    out['files'] = [f for f in out['all_files'] if wanted(f, sel)]
    return out


def set_info(m: dict | None) -> dict:
    """{set: {"size": bytes, "installed": bool}} from a manifest (all files, not only the selected ones)."""
    out = {s: {'size': 0, 'installed': False, 'files': 0} for s in (*SETS, 'shared')}
    if not m:
        return out
    root = config.models_root()
    for f in m.get('all_files', m.get('files', [])):
        s = f.get('set', 'shared')
        if s in out:
            out[s]['size'] += int(f.get('size', 0)); out[s]['files'] += 1
        elif s == 'shared':
            pass
    for s in SETS:
        fs = [f for f in m.get('all_files', m.get('files', [])) if f.get('set') == s]
        try:
            out[s]['installed'] = bool(fs) and all(_safe_path(root, f['path']).is_file() and _safe_path(root, f['path']).stat().st_size == f['size'] for f in fs)
        except (OSError, UpdateError):
            out[s]['installed'] = False
    return out


def remove_unselected(root: Path | None = None) -> list[str]:
    """Deletes the files of the sets that are not selected any more (listed in the installed manifest)."""
    root = root or config.models_root()
    p = root / 'manifest.json'
    removed = []
    try:
        m = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return removed
    sel = selected_sets()
    dirs = set()
    for f in m.get('files', []):
        if wanted(f, sel):
            continue
        try:
            t = _safe_path(root, f['path'])
            if t.is_file():
                t.unlink()
                # the .ok verification marker must go with the file, otherwise it
                # survives as an orphan and the emptied set folder cannot be removed
                try:
                    t.with_name(t.name + OK_SUFFIX).unlink()
                except OSError:
                    pass
                removed.append(f['path'])
                dirs.add(t.parent)
        except (OSError, UpdateError):
            pass
    for d in sorted(dirs, key=lambda x: len(x.parts), reverse=True):
        try:
            d.rmdir()
        except OSError:
            pass
    return removed


def installed_manifest() -> dict | None:
    p = config.models_root() / "manifest.json"
    try:
        m = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        if not isinstance(m, dict) or not isinstance(m.get('version'), str) or not isinstance(m.get('files'), list):
            return None
        return effective(m)
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


def files_to_fetch(manifest: dict, root: Path | None = None, verify: bool | None = None,
                   progress=None) -> list[dict]:
    """Entries that are missing or differ from the manifest.

    Files listed in the installed manifest with the same hash and size are trusted — but only while the version has not moved
    (verify=None decides that: a version change always re-hashes). A reused 1.3.4.1 install keeps the same paths and sizes with
    older bytes, and its own manifest can even claim the new hashes; trusting that record shrank the update to a ~32 MB diff of
    the new small files and applied it over the stale big ones. A successful hash is remembered in a .ok marker, so the
    expensive pass happens once. progress(done_bytes, total_bytes) is called while verifying so the UI is not frozen."""
    root = root or config.models_root()
    inst = installed_manifest()
    if verify is None:
        verify = bool(inst) and str(inst.get("version")) != str(manifest.get("version"))
    old = {f["path"]: f for f in (inst or {}).get("files", [])}
    skipped = _read_skipped_optional(root) if inst and inst.get("version") == manifest.get("version") else {}
    total = sum(int(f.get("size") or 0) for f in manifest["files"]) if verify else 0
    seen = 0
    todo = []
    for f in manifest["files"]:
        p = _safe_path(root, f["path"])
        ok = p.is_file() and p.stat().st_size == f["size"]
        if ok:
            trusted = f["path"] in old and old[f["path"]]["sha256"] == f["sha256"]
            if not trusted or verify:
                if _ok_marker_matches(p, f):
                    ok = True
                elif sha256_file(p) == f["sha256"]:
                    ok = True
                    _write_ok_marker(p, f)  # remember it: the next check is a stat, not a re-hash
                else:
                    ok = False
        if not ok and _is_skipped_optional(f, skipped):
            ok = True
        if not ok:
            todo.append(f)
        if verify and progress is not None:
            seen += int(f.get("size") or 0)
            try:
                progress(seen, total)
            except Exception:  # noqa: BLE001 — progress is cosmetic
                pass
    return todo


def _ok_marker_matches(path: Path, f: dict) -> bool:
    """True when a .ok marker beside the file records this manifest's hash and size."""
    try:
        rec = path.with_name(path.name + OK_SUFFIX).read_text(encoding="ascii").split()
        return len(rec) == 2 and rec[0] == f["sha256"] and rec[1] == str(f["size"])
    except (OSError, ValueError):
        return False


def _write_ok_marker(path: Path, f: dict) -> None:
    try:
        path.with_name(path.name + OK_SUFFIX).write_text(f'{f["sha256"]} {f["size"]}\n', encoding="ascii")
    except OSError:
        pass


def is_complete(manifest: dict | None = None, root: Path | None = None) -> bool:
    """True when every file of the manifest sits on the disk with the right size. Size-only on purpose: this runs on every status poll,
    so hashing gigabytes is not an option. Doubtful bytes (same size, different content) are caught by files_to_fetch(verify=True)."""
    m = manifest or installed_manifest()
    if not m:
        return False
    root = root or config.models_root()
    skipped = _read_skipped_optional(root)
    try:
        for f in m["files"]:
            p = _safe_path(root, f["path"])
            if p.is_file() and p.stat().st_size == f["size"]:
                continue
            if _is_skipped_optional(f, skipped):
                continue
            return False
        return True
    except (OSError, KeyError, TypeError, ValueError, UpdateError):  # unreadable or malformed state must not crash polling
        return False


# ---- Фоновая загрузка в staging + применение при перезапуске (как в Claude) ----

READY_NAME = "READY"  # флаг «готов к применению»: файл лежит в staging/<version>/READY
INSTALLER_READY_NAME = "INSTALLER_READY"  # флаг «инсталлер скачан и проверен»
INSTALLER_NAME = "Linda-Setup.exe"
ROLLBACK_LOG = "update_rollback.log"


def staging_root(root: Path | None = None) -> Path:
    """Корень фоновых загрузок: <data>/staging."""
    return (root or config.models_root()) / "staging"


def staging_dir(version: str, root: Path | None = None) -> Path:
    """Папка staging для одной версии: <data>/staging/<version>."""
    safe = "".join(c for c in str(version) if c.isalnum() or c in (".", "-", "_")) or "unknown"
    if safe in ('.', '..'):
        raise UpdateError('invalid staging version')
    return _safe_path(staging_root(root), safe)


def pending_status(root: Path | None = None) -> dict | None:
    """Что готово к применению после перезапуска. Баннер UI: «Перезапустите для обновления»."""
    base = staging_root(root)
    if not base.is_dir():
        return None
    found = []
    try:
        for d in base.iterdir():
            if d.is_dir() and (d / READY_NAME).is_file():
                found.append(d)
    except OSError:
        return None
    if not found:
        return None
    # самая новая версия — по имени папки
    found.sort(key=lambda p: vtuple(p.name), reverse=True)
    top = found[0]
    try:
        info = json.loads((top / READY_NAME).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        info = {}
    return {"version": info.get("version", top.name), "staging": str(top),
            "installer_ready": (top / INSTALLER_READY_NAME).is_file(),
            "banner": "Перезапустите для обновления"}


def _verify_staged(manifest: dict, staging: Path, root: Path, skipped: set[str] | None = None) -> None:
    """Повторная проверка хеша каждого файла: staged-копии или уже лежащие в data (неизменённые)."""
    validate_manifest(manifest)
    staged = {f["path"] for f in manifest["files"] if _safe_path(staging, f["path"]).is_file()}
    for f in manifest["files"]:
        if skipped and f["path"] in skipped and _is_optional_entry(f):
            continue
        src = _safe_path(staging if f["path"] in staged else root, f["path"])
        if not src.is_file() or src.stat().st_size != f["size"]:
            raise UpdateError(f"staged file missing: {f['path']}")
        if not _ok_marker_matches(src, f) and sha256_file(src) != f["sha256"]:
            raise UpdateError(f"checksum mismatch for {f['path']}")


def _cleanup_files(manifest: dict, root: Path, backup: Path, done: list) -> None:
    """Удаление файлов старых версий внутри управляемых папок (models/, calibration/)."""
    keep = {Path(f["path"]).as_posix() for f in manifest["files"]}
    keep |= {k + OK_SUFFIX for k in keep}  # keep the verification markers too
    for top in sorted({Path(f["path"]).parts[0] for f in manifest["files"]}):
        base = _safe_path(root, top)
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*"), reverse=True):
            rel = p.relative_to(root).as_posix()
            if p.is_file() and rel not in keep:
                _safe_path(root, rel)
                bkp = backup / rel
                bkp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, bkp)
                p.unlink()
                done.append((p, bkp))


def _apply_staged(manifest: dict, staging: Path, root: Path, raw: bytes | None = None,
                  skipped: dict[str, str] | None = None) -> list[str]:
    """Атомарная замена файлов из staging в data с бэкапом для отката. Возвращает применённые пути."""
    backup = staging / "backup"
    applied: list[str] = []
    done: list[tuple[Path, Path | None]] = []  # (цель, бэкап или None)
    validate_manifest(manifest)
    tmp = None
    try:
        for f in manifest["files"]:
            src = _safe_path(staging, f["path"])
            if not src.is_file():
                continue  # неизменённый файл уже лежит в data
            if not _ok_marker_matches(src, f) and sha256_file(src) != f["sha256"]:
                raise UpdateError(f"checksum mismatch for {f['path']}")
            dst = _safe_path(root, f["path"])
            dst.parent.mkdir(parents=True, exist_ok=True)
            bkp: Path | None = backup / f["path"]
            if dst.is_file():
                bkp.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, bkp)  # копия заменяемого файла — только изменённые
            else:
                bkp = None
            tmp = dst.with_name(dst.name + ".new")
            shutil.copy2(src, tmp)
            os.replace(tmp, dst)  # атомарная замена
            done.append((dst, bkp))
            applied.append(f["path"])
        _cleanup_files(manifest, root, backup, done)
        # Версия фиксируется внутри той же транзакции, после всех файлов.
        marker = root / 'manifest.json'
        old_marker = backup / 'manifest.json' if marker.is_file() else None
        if old_marker:
            old_marker.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(marker, old_marker)
        tmp = marker.with_suffix('.json.new')
        tmp.write_bytes(raw if raw is not None else json.dumps(manifest).encode('utf-8'))
        os.replace(tmp, marker)
        done.append((marker, old_marker))
        _write_skipped_optional(root, skipped or {})
        for f in manifest["files"]:
            dst = _safe_path(root, f["path"])
            if dst.is_file():
                _write_ok_marker(dst, f)
        return applied
    except Exception:
        # откат: восстанавливаем заменённые файлы из backup
        try:
            for dst, bkp in reversed(done):
                if bkp and bkp.is_file():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(bkp, dst)
                elif bkp is None:
                    dst.unlink(missing_ok=True)
            if tmp is not None:
                tmp.unlink(missing_ok=True)
            (root / ROLLBACK_LOG).write_text("Откат выполнен: файлы восстановлены из staging/backup\n", encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        raise


def apply_pending(root: Path | None = None) -> dict:
    """Применение при старте (до загрузки моделей): переносит READY-пакеты в data, чистит старый staging.

    Без сети, только файловые операции. При сбое — откат из backup, в ответе «Откат выполнен»."""
    root = root or config.models_root()
    base = staging_root(root)
    res: dict = {"applied": [], "version": None, "removed": [], "rolled_back": False, "error": ""}
    if not base.is_dir():
        return res
    try:
        dirs = sorted([d for d in base.iterdir() if d.is_dir()], key=lambda p: vtuple(p.name))
    except OSError as e:
        res["error"] = f"{type(e).__name__}: {e}"
        return res
    for d in dirs:
        ready = d / READY_NAME
        if not ready.is_file():
            continue
        try:
            staged_raw = (d / "manifest.json").read_bytes()
            verify_signature(staged_raw, (d / 'manifest.json.sig').read_bytes())
            m = effective(json.loads(staged_raw.decode('utf-8')))
        except Exception as e:  # noqa: BLE001
            res["error"] = f"bad staged manifest in {d.name}: {e}"
            continue
        try:
            _verify_staged(m, d, root)
            applied = _apply_staged(m, d, root, (d / "manifest.json").read_bytes())
            res["applied"] = applied
            res["version"] = m.get("version", d.name)
        except Exception as e:  # noqa: BLE001
            res["rolled_back"] = True
            res["error"] = ("Откат выполнен: %s" % e) if "Откат" not in str(e) else str(e)
            try:
                (root / ROLLBACK_LOG).write_text("Откат выполнен: %s: %s\n" % (type(e).__name__, e), encoding="utf-8")
            except OSError:
                pass
            continue
        try:
            shutil.rmtree(d, ignore_errors=True)  # старый staging удалён
            res["removed"].append(d.name)
        except OSError:
            pass
    # чистим пустые staging без READY (оборванные загрузки прошлых версий)
    try:
        for d in base.iterdir():
            if d.is_dir() and not (d / READY_NAME).is_file():
                try:
                    if not any(d.iterdir()):
                        d.rmdir()
                except OSError:
                    pass
    except OSError:
        pass
    return res


def prune_stale(root: Path | None = None) -> list[str]:
    """After a successful weights update: remove what the new manifest no longer owns but the file-level cleanup cannot see: ONNX caches of voices whose model folder is gone
    (old exports are ~1 GB each) and empty folders. Best effort, never raises."""
    root = Path(root or config.models_root())
    removed: list[str] = []
    try:
        models, onnx = root / "models", root / "onnx"
        if models.is_dir():
            for d in sorted(models.iterdir()):
                if d.is_dir() and not any(d.rglob("*")):
                    d.rmdir()
        if onnx.is_dir():
            for d in sorted(onnx.iterdir()):
                if d.is_dir() and not (models / d.name).is_dir():
                    shutil.rmtree(d, ignore_errors=True)
                    removed.append(f"onnx/{d.name}")
    except Exception:  # noqa: BLE001
        pass
    return removed


class Job:
    """Background download with progress; cancel() stops it between chunks (partial files are kept for resuming)."""

    def __init__(self):
        self.lock = threading.Lock()
        self._start_lock = threading.Lock()
        self.state = {"phase": "idle", "file": "", "done": 0, "total": 0, "error": "", "speed": 0.0, "version": "", "skipped_optional": [], "warning": ""}
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self.on_done = None
        self.apply_lock = None
        self._fetched = 0  # bytes of the current job written to staging, shared by the parallel workers
        self._fetched_lock = threading.Lock()

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
        with self._start_lock:
            if self.running():
                return False
            self._cancel.clear()
            with self._fetched_lock:
                self._fetched = 0
            self._set(phase="checking", file="", done=0, total=0, error="", speed=0.0, version=manifest["version"], skipped_optional=[], warning="")
            self._thread = threading.Thread(target=self._run, args=(manifest, raw, root or config.models_root(), (base_url or config.BASE_URL).rstrip("/")), daemon=True)
            self._thread.start()
            return True

    def _add_fetched(self, n: int, t0: float) -> None:
        """Progress counter shared by all workers: never below the reported total, never backwards."""
        with self._fetched_lock:
            self._fetched += n
            got = self._fetched
        el = max(time.time() - t0, 0.5)
        with self.lock:
            total = int(self.state.get("total") or 0)
            got = min(got, total) if total else got
            self.state.update(done=got, speed=got / el)

    def _run(self, manifest: dict, raw: bytes, root: Path, base: str) -> None:
        # Этап 1 — stage: фоновая загрузка только изменённых файлов в staging/<version>/ (таймауты, прогресс, отмена).
        # Этап 2 — проверка хеша каждого файла + флаг READY («Перезапустите для обновления»).
        # Этап 3 — apply: атомарная замена в data с бэкапом (откат при сбое). Применённый staging удаляется сразу.
        try:
            validate_manifest(manifest)
            # Reused 1.3.4.1 install: the previous manifest may claim the same paths/hashes while the bytes on disk differ, which
            # shrank the job to a ~32 MB "diff" of new files. Recompute the hash instead of trusting that record.
            self._set(phase="checking", file="", done=0, total=0)
            verify_t0 = time.time()

            def _verify_progress(done: int, total: int) -> None:
                # Hashing 3 GB takes seconds: show it, otherwise the banner sits at 0% and looks frozen.
                self._set(phase="checking", done=done, total=total, speed=(done / max(time.time() - verify_t0, 0.5)))

            todo = files_to_fetch(manifest, root, verify=True, progress=_verify_progress)
            staging = staging_dir(manifest["version"], root)
            staging.mkdir(parents=True, exist_ok=True)
            total = sum(f["size"] for f in todo)
            # Nothing to download (a reuse-only version bump): report 0/0 so the bar is not stuck at "0% of 3 GB" while verifying.
            self._set(total=total, done=0, phase="downloading" if todo else "verifying")
            t0 = time.time()
            skipped: dict[str, str] = {}
            if len(todo) > 1 and MAX_PARALLEL > 1:
                self._download_parallel(todo, staging, base, t0, skipped)
            else:
                for f in todo:
                    if self._cancel.is_set():
                        raise _Cancelled()
                    self._set(file=f["path"])
                    if not self._download_to(f, staging, base, t0):
                        skipped[f["path"]] = f["sha256"]
            self._set(phase="verifying", file="")
            (staging / "manifest.json").write_bytes(raw)  # манифест тоже кладём в staging
            signature = manifest.get('_signature', '').encode('ascii')
            verify_signature(raw, signature)
            (staging / 'manifest.json.sig').write_bytes(signature)
            _verify_staged(manifest, staging, root, skipped=set(skipped))  # повторная проверка хеша каждого файла
            (staging / READY_NAME).write_text(json.dumps({"version": manifest["version"], "ts": time.time()}), encoding="utf-8")
            self._set(phase="applying", file="")
            if getattr(self, "before_apply", None):
                try:
                    self.before_apply()  # release the files of the old models (the engine must not hold them open while they are replaced)
                except Exception:  # noqa: BLE001
                    pass
            with _apply_guard(self.apply_lock, self._cancel):
                _apply_staged(manifest, staging, root, raw, skipped=skipped)
            try:
                shutil.rmtree(staging, ignore_errors=True)  # применённый staging удаляем сразу: иначе дубль ~3 ГБ
            except OSError:
                pass
            prune_stale(root)
            self._set(phase="finishing", file="")
            skipped_list = sorted(skipped)
            warn = f"skipped missing optional file(s): {', '.join(skipped_list)}" if skipped_list else ""
            # Never report a finished job when files are still missing: the button would come back with no explanation.
            if not is_complete(manifest, root):
                left = files_to_fetch(manifest, root)
                raise UpdateError("model files are still incomplete after the update: %d file(s) missing" % len(left))
            self._set(phase="done", done=self.state["total"], file="", skipped_optional=skipped_list, warning=warn)
            if self.on_done:
                self.on_done(manifest)
        except _Cancelled:
            self._set(phase="cancelled", file="")
        except Exception as e:  # noqa: BLE001
            self._set(phase="error", file="", error=str(e) if isinstance(e, UpdateError) else f"{type(e).__name__}: {e}")

    def _download_parallel(self, todo: list, staging: Path, base: str, t0: float,
                           skipped: dict[str, str] | None = None) -> None:
        """Download several files concurrently (bounded by MAX_PARALLEL); progress is aggregated by _add_fetched,
        so concurrent workers can never push the bar backwards or leave it at 0 while bytes are arriving."""
        import concurrent.futures

        def one(f: dict) -> None:
            if self._cancel.is_set():
                raise _Cancelled()
            self._set(file=f["path"])
            # _download_to adds every byte it writes to the shared counter, so nothing is added here.
            if not self._download_to(f, staging, base, t0) and skipped is not None:
                skipped[f["path"]] = f["sha256"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_PARALLEL) as ex:
            futures = [ex.submit(one, f) for f in todo]
            err = None
            for fut in concurrent.futures.as_completed(futures):
                try:
                    fut.result()
                except Exception as e:  # noqa: BLE001
                    err = err or e
                    self._cancel.set()
            if err:
                raise err

    def _download_to(self, f: dict, staging: Path, base: str, t0: float) -> bool:
        """Скачивание одного файла в staging (докачка через .part, таймаут 30 с, проверка отмены между чанками). Возвращает False, если пропущен необязательный 404."""
        dest = staging / f["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        url = f"{base}/{urllib.parse.quote(f['path'])}"
        counted = 0  # bytes of this file already added to the job progress (survives retries without double counting)
        for attempt in range(4):
            try:
                have = part.stat().st_size if part.exists() else 0
                if have > f["size"]:
                    part.unlink()
                    have = 0
                if have and attempt == 0 and not counted:
                    # Bytes left over from an earlier run (resumable .part) were never counted in this job's counter.
                    counted = have
                    self._add_fetched(have, t0)
                h = hashlib.sha256()
                if have:
                    with open(part, "rb") as pf:
                        while chunk := pf.read(CHUNK):
                            h.update(chunk)
                if have < f["size"]:
                    r = _open(url, {"Range": f"bytes={have}-"} if have else None, timeout=15)
                    with r:
                        if have and getattr(r, "status", 200) != 206:  # server ignored Range: restart this file
                            have, h = 0, hashlib.sha256()
                            if counted:
                                self._add_fetched(-counted, t0)
                                counted = 0
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
                                if got > f['size']:
                                    raise UpdateError('download is larger than announced')
                                self._add_fetched(len(chunk), t0)
                if self._cancel.is_set():
                    raise _Cancelled()
                if part.stat().st_size != f["size"]:
                    raise ConnectionError(f"incomplete download of {f['path']}")
                if h.hexdigest() != f["sha256"]:
                    part.unlink(missing_ok=True)
                    raise UpdateError(f"checksum mismatch for {f['path']}")
                os.replace(part, dest)
                _write_ok_marker(dest, f)
                return True
            except (urllib.error.URLError, OSError, ConnectionError, http.client.HTTPException) as e:
                if isinstance(e, urllib.error.HTTPError) and e.code == 404 and _is_optional_entry(f):
                    _LOG.warning("optional file missing on server (HTTP 404), skipping: %s", f["path"])
                    part.unlink(missing_ok=True)
                    return False
                if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403, 404):
                    raise UpdateError(f"server refused {f['path']} (HTTP {e.code})") from e
                if attempt == 3:
                    raise UpdateError(f"network error while downloading {f['path']}: {e}") from e
                if self._cancel.wait(2 + attempt * 3):
                    raise _Cancelled()
        return True

    def _download(self, f: dict, root: Path, base: str, t0: float = 0.0) -> None:
        """Совместимость: прямое скачивание в data (теперь идёт через staging-папку версии)."""
        return self._download_to(f, staging_dir(self.state.get("version", ""), root), base, t0 or time.time())

    @staticmethod
    def _cleanup(manifest: dict, root: Path) -> None:
        """Remove files of older versions inside the managed folders (models/, calibration/)."""
        _cleanup_files(manifest, root, staging_dir(manifest['version'], root) / 'backup', [])


class _Cancelled(Exception):
    pass


def download_installer(info: dict, progress=None, cancel: threading.Event | None = None, version: str | None = None,
                        root: Path | None = None, manifest_raw: bytes | None = None, signature: str | None = None) -> Path:
    """Фоновая загрузка инсталлера в staging/<version>/ (таймаут 15 с, прогресс, отмена, проверка хеша).

    Качает в Linda-Setup.exe.part, после проверки хеша переименовывает в .exe и пишет INSTALLER_READY.
    Применение — только при перезапуске, сразу инсталлер не запускается."""
    if config.is_store_package():
        raise UpdateError('Application updates are managed by Microsoft Store / Windows package deployment')
    url = info["url"]
    if not url.startswith("https://") and not os.environ.get("LINDA_ALLOW_HTTP"):
        raise UpdateError("installer url must be https")
    ver = str(version or info.get("version") or "app")
    staging = staging_dir(ver, root)
    staging.mkdir(parents=True, exist_ok=True)
    dest = staging / INSTALLER_NAME
    part = staging / (INSTALLER_NAME + ".part")
    h = hashlib.sha256()
    have = part.stat().st_size if part.exists() else 0
    if have:
        with open(part, "rb") as pf:
            while chunk := pf.read(CHUNK):
                h.update(chunk)
    hdrs = {"Range": f"bytes={have}-"} if have else None
    with _open(url, hdrs, timeout=15) as r:
        if have and getattr(r, "status", 200) != 206:  # сервер не поддержал докачку: качаем заново
            part.unlink(missing_ok=True)
            h = hashlib.sha256()
            have = 0
        got = have
        total = int(info.get("size") or 0)
        with open(part, "ab" if have else "wb") as out:
            while True:
                if cancel is not None and cancel.is_set():
                    raise _Cancelled()
                chunk = r.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                got += len(chunk)
                if total and got > total:
                    raise UpdateError("installer is larger than announced")
                if progress:
                    progress(got, total)
    if cancel is not None and cancel.is_set():
        raise _Cancelled()
    if total and got != total:
        raise UpdateError("installer size mismatch")
    if h.hexdigest() != info["sha256"]:
        part.unlink(missing_ok=True)
        raise UpdateError("installer checksum mismatch")
    os.replace(part, dest)
    metadata = {"version": ver, "ts": time.time(), "sha256": info['sha256'], "size": got}
    if manifest_raw is not None and signature:
        metadata.update(manifest=base64.b64encode(manifest_raw).decode('ascii'), signature=signature)
    (staging / INSTALLER_READY_NAME).write_text(json.dumps(metadata), encoding="utf-8")
    return dest


def update_status(manifest: dict) -> dict:
    """Compare a verified manifest with what is installed and with this app."""
    inst = installed_version()
    out = {"remote_version": manifest["version"], "installed_version": inst, "notes": manifest.get("notes", ""),
           "weights_update": bool(inst) and vtuple(manifest["version"]) > vtuple(inst), "weights_missing": not is_complete(),
           "app_required": vtuple(manifest.get("min_app", "0")) > vtuple(config.APP_VERSION), "app_new": False, "installer": None}
    ins = manifest.get("installer")
    packaged = config.is_store_package()
    if packaged:
        out['distribution'] = 'store'
    if not packaged and ins and vtuple(ins.get("version", "0")) > vtuple(config.APP_VERSION):
        out["app_new"] = True
        out["installer"] = {"version": ins["version"], "size": ins.get("size", 0)}
    if out["weights_update"] or out["weights_missing"]:
        out["bytes_to_download"], out["files_to_download"] = _estimate_download(manifest)
    return out


def _estimate_download(manifest: dict) -> tuple[int, int]:
    """What this update is known to need, without hashing gigabytes on the status call.

    This is a floor, not a promise: when the version moved, the job re-hashes files the installed manifest merely claims are
    identical and downloads the ones that are not. Showing only the small diff here ("32 MB") is honest; the job's own total
    grows to the real figure as it verifies."""
    todo = files_to_fetch(manifest, verify=False)
    return sum(f["size"] for f in todo), len(todo)


def staged_installer(root: Path | None = None) -> dict | None:
    """Скачанный и проверенный инсталлер новее установленной версии: {"version", "path", "staging"}.
    Устаревшие папки staging (версия не новее текущей) удаляются: это наши временные файлы."""
    if config.is_store_package():
        return None
    base = staging_root(root)
    if not base.is_dir():
        return None
    best = None
    try:
        for d in base.iterdir():
            if not d.is_dir():
                continue
            setup = d / "Linda-Setup.exe"
            if not (d / INSTALLER_READY_NAME).is_file() or not setup.is_file():
                continue
            if vtuple(d.name) <= vtuple(config.APP_VERSION):
                shutil.rmtree(d, ignore_errors=True)
                continue
            try:
                meta = json.loads((d / INSTALLER_READY_NAME).read_text(encoding='utf-8'))
                if not isinstance(meta.get('sha256'), str) or len(meta['sha256']) != 64 or meta.get('size') != setup.stat().st_size:
                    continue
            except (OSError, ValueError, TypeError):
                continue
            if best is None or vtuple(d.name) > vtuple(best["version"]):
                best = {"version": d.name, "path": str(setup), "staging": str(d)}
    except OSError:
        return None
    return best


def verify_staged_installer(st: dict) -> None:
    """После паузы между скачиванием и перезапуском файл мог повредиться."""
    if config.is_store_package():
        raise UpdateError('EXE installers are not supported in Windows packages')
    path = Path(st['path'])
    meta = json.loads((path.parent / INSTALLER_READY_NAME).read_text(encoding='utf-8'))
    try:
        raw = base64.b64decode(meta['manifest'], validate=True)
        verify_signature(raw, meta['signature'].encode('ascii'))
        manifest = json.loads(raw.decode('utf-8'))
        info = manifest['installer']
        if os.environ.get('LINDA_DEV') == '1' and (manifest.get('channel') != 'dev' or info.get('app_id') != config.DEV_APP_ID):
            raise UpdateError('Dev cannot install a production update')
        if str(info['version']) != st['version']:
            raise ValueError('version mismatch')
    except (KeyError, ValueError, TypeError, UpdateError) as error:
        raise UpdateError('staged installer has no valid signed update proof; download it again') from error
    if path.stat().st_size != info.get('size') or sha256_file(path) != info.get('sha256'):
        raise UpdateError('staged installer checksum mismatch; download the update again')
