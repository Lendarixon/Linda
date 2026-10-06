"""Bounded process isolation for document parsing. No model/app imports."""
import json
from pathlib import Path
import sys
import threading

from .document_worker import MAX_INPUT, MAX_TEXT

TIMEOUT = 20
_slots = threading.BoundedSemaphore(2)


def _command(filename, source, target):
    args = [filename,str(source),str(target)]
    if getattr(sys,'frozen',False):
        return [sys.executable,'--document-worker',*args]
    return [sys.executable,'-m','linda_desktop.document_worker',*args]


def extract(filename, content):
    if len(content)>MAX_INPUT:
        raise ValueError('Document exceeds the supported input limit')
    ext = Path(filename).suffix.lower()
    if ext in ('.txt','.md','.text',''):
        head = content[:4096]
        utf16 = head.startswith((b'\xff\xfe', b'\xfe\xff'))
        if b'\x00' in head and not utf16:  # NUL-байты вне UTF-16: это не текст (например, .exe под видом .txt)
            raise ValueError('not a text file')
        if utf16:
            return content.decode('utf-16', errors='replace').lstrip('\ufeff')
        try:
            return content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                return content.decode('cp1251')  # старые русские файлы Windows; cp1252 для них давал бы кракозябры
            except UnicodeDecodeError:
                return content.decode('cp1252',errors='replace')
    if ext not in ('.pdf','.docx'):
        raise ValueError('Supported formats: .txt, .md, .docx, .pdf')
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
