"""Bounded process isolation for document parsing. No model/app imports."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
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
        try:
            return content.decode('utf-8-sig')
        except UnicodeDecodeError:
            return content.decode('cp1252',errors='replace')
    if ext not in ('.pdf','.docx'):
        raise ValueError('Supported formats: .txt, .md, .docx, .pdf')
    if not _slots.acquire(timeout=TIMEOUT):
        raise ValueError('Document parser is busy; try again')
    try:
        with tempfile.TemporaryDirectory(prefix='linda-document-') as directory:
            source, target = Path(directory)/'input', Path(directory)/'output.json'
            source.write_bytes(content)
            env = dict(os.environ,OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1')
            flags = subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            with subprocess.Popen(_command('document'+ext,source,target),cwd=Path(__file__).resolve().parents[1],
                                  env=env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                                  creationflags=flags) as process:
                try:
                    process.wait(timeout=TIMEOUT)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                    raise ValueError('Document parsing timed out') from None
                if process.returncode:
                    raise ValueError('Document parser stopped unexpectedly')
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
