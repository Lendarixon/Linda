from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable

import trace_config as config


class UpdateError(Exception):
    """An update operation failed."""


_Q = 2**252 + 27742317777372353535851937790883648493
_L = 2**255 - 19
_D = (-121665 * pow(121666, _L - 2, _L)) % _L
_I = pow(2, (_L - 1) // 4, _L)
_IDENTITY = (0, 1, 1, 0)
_G = (4 * pow(5, _L - 2, _L) % _L, 0, 0, 0)
_G = (_G[0], (_G[0] * _G[0] - 1) * pow(_D * _G[0] * _G[0] + 1, _L - 2, _L) % _L, 1,
      _G[0] * ((_G[0] * _G[0] - 1) * pow(_D * _G[0] * _G[0] + 1, _L - 2, _L)) % _L)


def _add(p: tuple[int, int, int, int], q: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Add extended Edwards points."""
    x1, y1, z1, t1 = p
    x2, y2, z2, t2 = q
    a = (y1 - x1) * (y2 - x2) % _L
    b = (y1 + x1) * (y2 + x2) % _L
    c = 2 * _D * t1 * t2 % _L
    d = 2 * z1 * z2 % _L
    e, f, g, h = (b - a) % _L, (d - c) % _L, (d + c) % _L, (b + a) % _L
    return e * f % _L, g * h % _L, f * g % _L, e * h % _L


def _mul(point: tuple[int, int, int, int], scalar: int) -> tuple[int, int, int, int]:
    """Multiply an Edwards point by an integer."""
    result = _IDENTITY
    addend = point
    while scalar:
        if scalar & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        scalar >>= 1
    return result


def _compress(point: tuple[int, int, int, int]) -> bytes:
    """Encode an Edwards point."""
    x, y, z, _ = point
    zi = pow(z, _L - 2, _L)
    x, y = x * zi % _L, y * zi % _L
    return int.to_bytes(y | ((x & 1) << 255), 32, 'little')


def _decompress(encoded: bytes) -> tuple[int, int, int, int]:
    """Decode a compressed Edwards point."""
    if len(encoded) != 32:
        raise ValueError('invalid point length')
    value = int.from_bytes(encoded, 'little')
    sign, y = value >> 255, value & ((1 << 255) - 1)
    if y >= _L:
        raise ValueError('invalid point')
    u, v = (y * y - 1) % _L, (_D * y * y + 1) % _L
    xx = u * pow(v, _L - 2, _L) % _L
    x = pow(xx, (_L + 3) // 8, _L)
    if (x * x - xx) % _L:
        x = x * _I % _L
    if (x * x - xx) % _L:
        raise ValueError('invalid point')
    if x & 1 != sign:
        x = _L - x
    return x, y, 1, x * y % _L


def _base_point() -> tuple[int, int, int, int]:
    """Return the Ed25519 base point."""
    return _decompress(bytes.fromhex('5866666666666666666666666666666666666666666666666666666666666666'))


_G = _base_point()


def vtuple(v: str) -> tuple[int, ...]:
    """Convert a dotted version to integer components."""
    try:
        parts = tuple(int(part) for part in v.split('.'))
        if not parts or any(part < 0 for part in parts):
            raise ValueError
        return parts
    except (AttributeError, ValueError):
        raise UpdateError('invalid version') from None


def _check_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme == 'https' and parsed.hostname:
        return
    if (parsed.scheme == 'http' and os.environ.get('TRACE_ALLOW_HTTP') == '1'
            and parsed.hostname in ('127.0.0.1', 'localhost', '::1')):
        return
    raise UpdateError('update server URL must use HTTPS')


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        if urllib.parse.urlsplit(req.full_url).scheme == 'https' and urllib.parse.urlsplit(newurl).scheme != 'https':
            raise UpdateError('update server URL must use HTTPS')
        _check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url: str, headers: dict[str, str] | None = None, timeout: float = 30) -> Any:
    """Open a permitted update URL."""
    _check_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': f'LindaTrace/{config.APP_VERSION}', **(headers or {})})
    return urllib.request.build_opener(_SafeRedirect()).open(request, timeout=timeout)


def fetch_bytes(url: str, timeout: float = 30, limit: int = 4_000_000) -> bytes:
    """Fetch a bounded response body."""
    try:
        with _open(url, timeout=timeout) as response:
            data = response.read(limit + 1)
        if len(data) > limit:
            raise UpdateError('update response is too large')
        return data
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            message = 'update information was not found on the server'
        elif exc.code in (401, 403):
            message = 'the update server denied access'
        else:
            message = f'update server returned HTTP {exc.code}'
        raise UpdateError(message) from exc
    except UpdateError:
        raise
    except (urllib.error.URLError, OSError) as exc:
        raise UpdateError(f'cannot reach the update server: {exc}') from exc


def verify_signature(raw: bytes, sig_b64: bytes | str, pubkey_b64: str | None = None) -> None:
    """Verify an Ed25519 signature over exact message bytes."""
    try:
        sig = base64.b64decode(sig_b64, validate=True)
        public = base64.b64decode(pubkey_b64 or config.SIGNING_PUBKEY_B64, validate=True)
        if len(sig) != 64 or len(public) != 32:
            raise ValueError
        r_encoded, s_encoded = sig[:32], sig[32:]
        scalar = int.from_bytes(s_encoded, 'little')
        if scalar >= _Q:
            raise ValueError
        r_point, a_point = _decompress(r_encoded), _decompress(public)
        h = int.from_bytes(hashlib.sha512(r_encoded + public + raw).digest(), 'little') % _Q
        if _compress(_mul(_G, scalar)) != _compress(_add(r_point, _mul(a_point, h))):
            raise ValueError
    except Exception as exc:
        raise UpdateError('update manifest signature is invalid') from exc


def validate_manifest(m: Any) -> None:
    """Validate a decoded update manifest."""
    malformed = UpdateError('update manifest is malformed')
    try:
        if not isinstance(m, dict) or m.get('schema') != 1 or not isinstance(m.get('version'), str) or not m['version'].strip():
            raise malformed
        vtuple(m['version'])
        if 'min_app' in m:
            if not isinstance(m['min_app'], str):
                raise malformed
            vtuple(m['min_app'])
        files = m.get('files')
        if not isinstance(files, list) or len(files) > 50:
            raise malformed
        seen: set[str] = set()
        for entry in files:
            if not isinstance(entry, dict):
                raise malformed
            path, size, digest = entry.get('path'), entry.get('size'), entry.get('sha256')
            if (not isinstance(path, str) or not re.fullmatch(r'models/[A-Za-z0-9._-]+', path)
                    or path in seen or type(size) is not int or not 0 <= size <= 250_000_000
                    or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                raise malformed
            seen.add(path)
        installer = m.get('installer')
        if installer is not None:
            if not isinstance(installer, dict) or not isinstance(installer.get('version'), str):
                raise malformed
            vtuple(installer['version'])
            url, size, digest = installer.get('url'), installer.get('size'), installer.get('sha256')
            valid_url = isinstance(url, str) and (url.startswith('https://') or
                         (os.environ.get('TRACE_ALLOW_HTTP') == '1' and url.startswith('http://')))
            if (not valid_url or type(size) is not int or size <= 0
                    or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)
                    or installer.get('app_id') != config.APP_ID):
                raise malformed
    except UpdateError as exc:
        if str(exc) == 'update manifest is malformed':
            raise
        raise malformed from exc
    except Exception as exc:
        raise malformed from exc


def get_manifest(base_url: str | None = None) -> tuple[dict[str, Any], bytes]:
    """Fetch, authenticate, and validate the current manifest."""
    base = (base_url or config.BASE_URL).rstrip('/')
    raw = fetch_bytes(f'{base}/{config.MANIFEST_NAME}')
    sig = fetch_bytes(f'{base}/{config.SIGNATURE_NAME}', limit=1024)
    verify_signature(raw, sig)
    try:
        manifest = json.loads(raw.decode('utf-8'))
    except Exception as exc:
        raise UpdateError('update manifest is malformed') from exc
    validate_manifest(manifest)
    manifest['_signature'] = sig.decode('ascii').strip()
    return manifest, raw


def installed_manifest() -> dict[str, Any] | None:
    """Read a valid installed manifest marker."""
    try:
        data = json.loads((config.models_root() / 'manifest.json').read_text(encoding='utf-8'))
        validate_manifest(data)
        return data
    except Exception:
        return None


def installed_version() -> str | None:
    """Return the installed model pack version."""
    manifest = installed_manifest()
    return manifest.get('version') if manifest else None


_HASH_CACHE: dict[tuple[str, int, int], str] = {}


def _hash_file(path: Path) -> str:
    stat = path.stat()
    key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    if key not in _HASH_CACHE:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        _HASH_CACHE[key] = digest.hexdigest()
    return _HASH_CACHE[key]


def active_model_path(name: str, bundled: Path) -> Path:
    """Return a verified installed model or the bundled fallback."""
    manifest = installed_manifest()
    entry_path = f'models/{name}'
    entry = next((e for e in manifest.get('files', []) if e.get('path') == entry_path), None) if manifest else None
    if entry:
        path = config.models_root() / entry_path
        try:
            if path.is_file() and path.stat().st_size == entry['size'] and _hash_file(path) == entry['sha256']:
                return path
        except OSError:
            pass
    return bundled


def active_model_info(name: str, bundled: Path) -> dict[str, str]:
    """Describe the active model file."""
    path = active_model_path(name, bundled)
    if path != bundled:
        manifest = installed_manifest() or {}
        entry = next(e for e in manifest.get('files', []) if e.get('path') == f'models/{name}')
        return {'source': 'downloaded', 'version': manifest['version'], 'sha256': entry['sha256']}
    digest = _hash_file(bundled) if bundled.is_file() else ''
    return {'source': 'bundled', 'version': config.BUNDLED_MODEL_VERSION, 'sha256': digest}


def files_to_fetch(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Return files absent or different in the installed pack."""
    root = config.models_root()
    result = []
    for entry in manifest['files']:
        path = root / entry['path']
        try:
            same = path.is_file() and path.stat().st_size == entry['size'] and _hash_file(path) == entry['sha256']
        except OSError:
            same = False
        if not same:
            result.append(entry)
    return result


def update_status(manifest: dict[str, Any]) -> dict[str, Any]:
    """Summarize available model and application updates."""
    current = installed_version() or config.BUNDLED_MODEL_VERSION
    installer = manifest.get('installer')
    remote = manifest['version']
    model_update = vtuple(remote) > vtuple(current)
    return {
        'remote_version': remote, 'installed_version': current, 'notes': manifest.get('notes', ''),
        'model_update': model_update,
        'app_required': vtuple(manifest.get('min_app', '0')) > vtuple(config.APP_VERSION),
        'app_new': bool(installer and vtuple(installer['version']) > vtuple(config.APP_VERSION)),
        'installer': {'version': installer['version'], 'size': installer['size']} if installer else None,
        'bytes_to_download': sum(e['size'] for e in files_to_fetch(manifest)) if model_update else 0,
    }


def check_for_updates(base_url: str | None = None, include_raw: bool = False) -> dict[str, Any]:
    """Check the signed update manifest."""
    manifest, raw = get_manifest(base_url)
    result = update_status(manifest)
    if include_raw:
        result.update(manifest=manifest, raw=raw)
    return result


class Job:
    """Download and atomically apply one model pack."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or config.BASE_URL).rstrip('/')
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._status: dict[str, Any] = {'phase': 'idle', 'file': '', 'done': 0, 'total': 0,
                                       'error': '', 'version': ''}

    def status(self) -> dict[str, Any]:
        """Return a copy of the current job status."""
        with self._lock:
            return dict(self._status)

    def cancel(self) -> None:
        """Request cancellation between download chunks."""
        self._cancel.set()

    def start(self, manifest: dict[str, Any], raw: bytes,
              on_done: Callable[[dict[str, Any]], Any] | None = None) -> bool:
        """Start a worker unless one is already active."""
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._cancel.clear()
            self._status = {'phase': 'checking', 'file': '', 'done': 0, 'total': 0,
                            'error': '', 'version': str(manifest.get('version', ''))}
            self._thread = threading.Thread(target=self._run, args=(manifest, raw, on_done), daemon=True)
            self._thread.start()
            return True

    def _set(self, **values: Any) -> None:
        with self._lock:
            self._status.update(values)

    def _download(self, url: str, part: Path, size: int) -> None:
        part.parent.mkdir(parents=True, exist_ok=True)
        existing = part.stat().st_size if part.exists() else 0
        if existing > size:  # stale or foreign leftover: start over
            part.unlink()
            existing = 0
        if existing == size and size:  # already complete (interrupted before the rename): the hash check decides
            return
        headers = {'Range': f'bytes={existing}-'} if existing else {}
        with _open(url, headers=headers) as response:
            if existing and getattr(response, 'status', response.getcode()) != 206:
                existing = 0
                part.write_bytes(b'')
            mode = 'ab' if existing else 'wb'
            done = existing
            with part.open(mode) as target:
                while True:
                    if self._cancel.is_set():
                        raise InterruptedError('cancelled')
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
                    done += len(chunk)
                    self._set(done=done)
        if part.stat().st_size != size:
            raise UpdateError('downloaded file size mismatch')

    def _run(self, manifest: dict[str, Any], raw: bytes,
             on_done: Callable[[dict[str, Any]], Any] | None) -> None:
        stage = config.models_root() / '.staging' / str(manifest.get('version', 'invalid'))
        try:
            validate_manifest(manifest)
            # The caller passes what get_manifest() returned; re-check that the bytes we are about to store as the
            # installed marker really are the signed ones and describe exactly this manifest.
            verify_signature(raw, manifest.get('_signature', ''))
            signed = json.loads(raw.decode('utf-8'))
            if {k: v for k, v in manifest.items() if k != '_signature'} != signed:
                raise UpdateError('update manifest is malformed')
            current = installed_version() or config.BUNDLED_MODEL_VERSION
            if vtuple(manifest['version']) <= vtuple(current):
                raise UpdateError('model pack is not newer')
            entries = files_to_fetch(manifest)
            total = sum(e['size'] for e in entries)
            self._set(phase='downloading', total=total, done=0)
            for entry in entries:
                if self._cancel.is_set():
                    raise InterruptedError('cancelled')
                name = entry['path'].split('/', 1)[1]
                part = stage / 'models' / f'{name}.part'
                self._set(file=entry['path'])
                self._download(f'{self.base_url}/{entry["path"]}', part, entry['size'])
                if _hash_file(part) != entry['sha256']:
                    raise UpdateError('downloaded model checksum mismatch')
                part.replace(part.with_suffix(''))
            self._set(phase='verifying', file='')
            for entry in entries:  # only what was downloaded: unchanged files stay where they are
                staged = stage / entry['path']
                if not staged.is_file() or staged.stat().st_size != entry['size'] or _hash_file(staged) != entry['sha256']:
                    raise UpdateError('staged model checksum mismatch')
            if self._cancel.is_set():
                raise InterruptedError('cancelled')
            self._set(phase='applying')
            root = config.models_root()
            models = root / 'models'
            backup = stage / 'backup'
            applied: list[tuple[Path, Path | None]] = []
            marker_tmp = root / 'manifest.json.tmp'
            marker = root / 'manifest.json'
            root.mkdir(parents=True, exist_ok=True)
            try:
                for entry in entries:
                    target = root / entry['path']
                    target.parent.mkdir(parents=True, exist_ok=True)
                    old = None
                    if target.exists():
                        old = backup / entry['path']
                        old.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(target, old)
                    applied.append((target, old))
                    os.replace(stage / entry['path'], target)
                marker_tmp.write_bytes(raw)
                applied.append((marker, marker.with_suffix('.json.backup') if marker.exists() else None))
                if marker.exists():
                    shutil.copy2(marker, marker.with_suffix('.json.backup'))
                os.replace(marker_tmp, marker)
                marker.with_suffix('.json.backup').unlink(missing_ok=True)
            except Exception:
                for target, old in reversed(applied):  # keep going if one restore step fails: restore as much as possible
                    try:
                        if old and old.exists():
                            shutil.copy2(old, target) if target == marker else os.replace(old, target)
                        else:
                            target.unlink(missing_ok=True)
                    except OSError:
                        pass
                marker_tmp.unlink(missing_ok=True)
                raise
            if on_done:
                on_done(manifest)
            shutil.rmtree(stage, ignore_errors=True)
            self._set(phase='done', file='', error='')
        except InterruptedError:
            self._set(phase='cancelled', error='cancelled')
        except Exception as exc:
            self._set(phase='error', error=str(exc) or exc.__class__.__name__)


def download_installer(info: dict[str, Any], raw: bytes, signature: str,
                       progress: Callable[[int, int], Any] | None = None,
                       cancel: threading.Event | None = None, root: Path | None = None) -> Path:
    """Download and stage a signed application installer."""
    root = root or config.models_root()
    stage = root / '.staging' / 'installer' / info['version']
    part = stage / 'LindaTrace-Setup.exe.part'
    stage.mkdir(parents=True, exist_ok=True)
    existing = part.stat().st_size if part.exists() else 0
    if existing > info['size']:
        part.unlink()
        existing = 0
    headers = {'Range': f'bytes={existing}-'} if existing else {}
    try:
        if existing != info['size']:  # a complete .part only needs the hash check below
            with _open(info['url'], headers=headers) as response:
                if existing and getattr(response, 'status', response.getcode()) != 206:
                    existing = 0
                    part.write_bytes(b'')
                done = existing
                with part.open('ab' if existing else 'wb') as out:
                    while True:
                        if cancel and cancel.is_set():
                            raise InterruptedError('cancelled')
                        data = response.read(64 * 1024)
                        if not data:
                            break
                        out.write(data)
                        done += len(data)
                        if info['size'] and done > info['size']:
                            raise UpdateError('installer is larger than announced')
                        if progress:
                            progress(done, info['size'])
        if part.stat().st_size != info['size'] or _hash_file(part) != info['sha256']:
            part.unlink(missing_ok=True)
            raise UpdateError('installer checksum mismatch')
        final = stage / 'LindaTrace-Setup.exe'
        os.replace(part, final)
        ready = {'version': info['version'], 'sha256': info['sha256'], 'size': info['size'],
                 'manifest': base64.b64encode(raw).decode('ascii'), 'signature': signature}
        (stage / 'INSTALLER_READY.json').write_text(json.dumps(ready), encoding='utf-8')
        return final
    except InterruptedError as exc:
        raise UpdateError('installer download cancelled') from exc


def staged_installer(root: Path | None = None) -> dict[str, Any] | None:
    """Return the newest valid-looking staged installer."""
    root = root or config.models_root()
    base = root / '.staging' / 'installer'
    candidates = []
    if not base.exists():
        return None
    for folder in base.iterdir():
        try:
            version = folder.name
            if vtuple(version) <= vtuple(config.APP_VERSION):
                shutil.rmtree(folder, ignore_errors=True)
                continue
            meta = json.loads((folder / 'INSTALLER_READY.json').read_text(encoding='utf-8'))
            exe = folder / 'LindaTrace-Setup.exe'
            if meta['version'] == version and exe.is_file() and exe.stat().st_size == meta['size']:
                candidates.append((vtuple(version), {'version': version, 'path': exe, 'staging': folder}))
        except Exception:
            continue
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def verify_staged_installer(st: dict[str, Any]) -> None:
    """Authenticate staged installer metadata and bytes."""
    try:
        meta = json.loads((Path(st['staging']) / 'INSTALLER_READY.json').read_text(encoding='utf-8'))
        raw = base64.b64decode(meta['manifest'], validate=True)
        verify_signature(raw, meta['signature'])
        manifest = json.loads(raw.decode('utf-8'))
        validate_manifest(manifest)
        installer = manifest['installer']
        path = Path(st['path'])
        if (installer['sha256'] != _hash_file(path) or installer['app_id'] != config.APP_ID
                or installer['version'] != meta['version'] or installer['size'] != path.stat().st_size):
            raise ValueError
    except Exception as exc:
        raise UpdateError('staged installer verification failed') from exc


def _ps_quote(value: str) -> str:
    """Quote text as a PowerShell single-quoted literal."""
    return "'" + value.replace("'", "''") + "'"


def launch_installer(path: Path, wait_pid: int | None = None) -> bool:
    """Launch an already verified installer silently.

    Setup cannot close a running Linda Trace itself (a server process has no window to receive the close request and
    Setup then aborts), so with wait_pid the launch waits (at most 60 s) until that process has exited."""
    flags = 0
    if sys.platform == 'win32':
        new_group = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0x00000200)
        # powershell.exe does not run at all when started DETACHED_PROCESS (verified); it needs CREATE_NO_WINDOW instead.
        flags = new_group | (getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000) if wait_pid
                             else getattr(subprocess, 'DETACHED_PROCESS', 0x00000008))
    log = Path(path).with_name('setup.log')  # next to the staged installer: the only trace if the silent update fails
    args = ['/SILENT', '/SUPPRESSMSGBOXES', '/CLOSEAPPLICATIONS', '/RESTARTAPPLICATIONS', '/RELAUNCH=1']
    if wait_pid:
        arg_string = ' '.join(args) + f' /LOG="{log}"'
        trace = _ps_quote(str(Path(path).with_name('launcher.log')))  # what the helper did and when, for support
        script = (f"Add-Content -LiteralPath {trace} ('waiting for pid {int(wait_pid)} ' + (Get-Date -Format o)); "
                  f"try {{ Wait-Process -Id {int(wait_pid)} -Timeout 60 -ErrorAction Stop }} catch {{ Add-Content -LiteralPath {trace} ('wait: ' + $_) }}; "
                  f"Add-Content -LiteralPath {trace} ('starting installer ' + (Get-Date -Format o)); "
                  f"Start-Process -FilePath {_ps_quote(str(path))} -ArgumentList {_ps_quote(arg_string)}")
        command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-Command', script]
    else:
        command = [str(path), *args, f'/LOG={log}']
    subprocess.Popen(command, close_fds=True, creationflags=flags, stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True
