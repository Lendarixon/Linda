"""One short-lived restart draft, subject to the same storage policy as history."""
import json
import os
import secrets
import tempfile
import threading
import time
from . import config
from .engine import load_settings

_lock = threading.Lock()
MAX_CHARS = 1_000_000

def _path():
    return config.data_dir() / 'restart-draft.json'

def allowed():
    return not config.enterprise().get('disable_history') and load_settings().get('save_history', True)

def save(text):
    if not isinstance(text, str) or len(text) > MAX_CHARS:
        raise ValueError('Save the document before updating: the restart draft is too large.')
    if not allowed():
        raise PermissionError('Restart draft storage is disabled by history settings or policy.')
    with _lock:
        path = _path()
        if not text.strip():
            path.unlink(missing_ok=True)
            return
        draft = {'id':secrets.token_hex(16),'text':text,'ts':time.time()}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix='draft-',suffix='.tmp',delete=False) as stream:
                temporary = stream.name
                json.dump(draft,stream,ensure_ascii=False)
            if not allowed():
                raise PermissionError('Restart draft storage is disabled by policy.')
            os.replace(temporary,path)
        finally:
            if temporary and os.path.exists(temporary):
                os.unlink(temporary)

def read():
    with _lock:
        path = _path()
        try:
            if not allowed():
                path.unlink(missing_ok=True)
                return None
            if path.stat().st_size > 6_000_000:
                raise ValueError('invalid draft size')
            draft = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(draft.get('text'),str) or len(draft['text']) > MAX_CHARS or not isinstance(draft.get('id'),str) or time.time()-float(draft['ts']) > 86400:
                raise ValueError('invalid or expired draft')
            return draft
        except FileNotFoundError:
            return None
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return None

def acknowledge(identity):
    with _lock:
        path = _path()
        try:
            draft = json.loads(path.read_text(encoding='utf-8'))
            if draft.get('id') != identity:
                return False
            path.unlink()
            return True
        except (OSError, ValueError, TypeError, AttributeError):
            return False
