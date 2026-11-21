"""Bounded process isolation for document parsing. No model/app imports."""
import json
from pathlib import Path
import sys
import threading

from .document_worker import MAX_INPUT, MAX_TEXT
from .document_formats import PLAIN_EXTS, SUPPORTED_EXTS

TIMEOUT = 20
_slots = threading.BoundedSemaphore(2)


def _command(filename, source, target):
    args = [filename,str(source),str(target)]
    if getattr(sys,'frozen',False):
        return [sys.executable,'--document-worker',*args]
    return [sys.executable,'-m','linda_desktop.document_worker',*args]


def _bounded_text(text):
    if len(text.encode('utf-8')) > MAX_TEXT:
        raise ValueError('Extracted text exceeds the supported limit')
    return text


def extract(filename, content):
    if len(content)>MAX_INPUT:
        raise ValueError('Document exceeds the supported input limit')
    ext = Path(filename).suffix.lower()
    if ext in PLAIN_EXTS or ext=='':
        head = content[:4096]
        utf16 = head.startswith((b'\xff\xfe', b'\xfe\xff'))
        if b'\x00' in head and not utf16:  # NUL-байты вне UTF-16: это не текст (например, .exe под видом .txt)
            raise ValueError('not a text file')
        if utf16:
            text = content.decode('utf-16', errors='replace').lstrip('\ufeff')
            return _bounded_text(text)
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('cp1251')  # старые русские файлы Windows; cp1252 для них давал бы кракозябры
            except UnicodeDecodeError:
                text = content.decode('cp1252',errors='replace')
        return _bounded_text(text)
    if ext in ('.ppt','.pptx'):
        raise ValueError('PowerPoint files are not supported. Slide text is not suitable for reliable authorship analysis, even when exported to PDF')
    if ext not in SUPPORTED_EXTS:
        raise ValueError('Unsupported document format')
    if not _slots.acquire(timeout=TIMEOUT):
        raise ValueError('Document parser is busy; try again')
    try:
        from .document_sandbox import scratch_job
        with scratch_job() as directory:
            source, target = Path(directory)/'input', Path(directory)/'output.json'
            source.write_bytes(content)
            from .document_sandbox import parse_worker
            parse_worker('document'+ext,source,target,TIMEOUT)
            if not target.is_file() or target.stat().st_size>MAX_TEXT*2+2048:
                raise ValueError('Document parser returned an invalid response')
            try:
                result = json.loads(target.read_text(encoding='utf-8'))
                if result.get('error'):
                    raise ValueError(str(result['error'])[:240])
                text = result['text']
                if not isinstance(text,str) or len(text.encode('utf-8'))>MAX_TEXT:
                    raise KeyError('text')
                return text
            except (KeyError,TypeError,json.JSONDecodeError,UnicodeDecodeError):
                raise ValueError('Document parser returned an invalid response') from None
    finally:
        _slots.release()
