"""One short-lived restart draft, subject to the same storage policy as history."""
import json
import math
import secrets
import threading
import time
from . import config, protected_storage
from .engine import load_settings

_lock = threading.Lock()
MAX_CHARS = 1_000_000
_PURPOSE = 'restart-draft'

def _path():
    return config.data_dir() / 'restart-draft.json'

def allowed():
    return not config.enterprise().get('disable_history') and load_settings().get('save_history', True)


def _encode(draft):
    return json.dumps(draft, ensure_ascii=False, allow_nan=False).encode('utf-8')


def _write(path, draft):
    # Only ciphertext is ever handed to atomic_write and its temporary file.
    ciphertext = protected_storage.protect(_encode(draft), _PURPOSE)
    if not allowed():
        raise PermissionError('Restart draft storage is disabled by policy.')
    protected_storage.atomic_write(path, ciphertext)


def _read_locked(path):
    if not allowed():
        path.unlink(missing_ok=True)
        return None
    try:
        if path.stat().st_size > 6_000_000:
            raise ValueError('invalid draft size')
        stored = path.read_bytes()
        legacy = not stored.startswith(protected_storage.MAGIC)
        raw = stored if legacy else protected_storage.unprotect(stored, _PURPOSE)
        draft = json.loads(raw.decode('utf-8'))
        if (not isinstance(draft.get('text'), str) or len(draft['text']) > MAX_CHARS
                or not isinstance(draft.get('id'), str) or not draft['id']
                or not math.isfinite(float(draft['ts']))):
            raise ValueError('invalid draft')
        if time.time() - float(draft['ts']) > 86400:
            path.unlink(missing_ok=True)
            return None
        if legacy:
            # Preserve the exact nonce and timestamp; the UI may already have it.
            _write(path, draft)
        return draft
    except FileNotFoundError:
        return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RuntimeError, OverflowError):
        # Corruption/wrong account must not destroy the only recovery copy.
        return None


def save(text):
    if not isinstance(text, str) or len(text) > MAX_CHARS:
        raise ValueError('Save the document before updating: the restart draft is too large.')
    if not allowed():
        raise PermissionError('Restart draft storage is disabled by history settings or policy.')
    with _lock:
        path = _path()
        with protected_storage.storage_lock(path):
            if not allowed():
                raise PermissionError('Restart draft storage is disabled by policy.')
            if not text.strip():
                path.unlink(missing_ok=True)
                return
            draft = {'id':secrets.token_hex(16),'text':text,'ts':time.time()}
            _write(path, draft)

def read():
    with _lock:
        path = _path()
        try:
            with protected_storage.storage_lock(path):
                return _read_locked(path)
        except (OSError, RuntimeError):
            return None

def acknowledge(identity):
    with _lock:
        path = _path()
        try:
            with protected_storage.storage_lock(path):
                draft = _read_locked(path)
                if draft is None or draft['id'] != identity:
                    return False
                path.unlink()
                return True
        except (OSError, ValueError, TypeError, AttributeError, RuntimeError):
            return False
