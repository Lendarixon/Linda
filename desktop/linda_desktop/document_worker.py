"""Disposable parser; deliberately imports no app, engine, or model modules."""
import ctypes
import io
import json
import os
from pathlib import Path
import sys
import zipfile

MAX_INPUT = 20_000_000
MAX_TEXT = 4_000_000
MAX_PAGES = 500
_job = None


def limit_memory():
    """Hard worker process-memory ceiling on Windows; not a security sandbox."""
    if os.name != 'nt':
        return
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('per_process_time',ctypes.c_int64),('per_job_time',ctypes.c_int64),
                    ('flags',w.DWORD),('min_ws',ctypes.c_size_t),('max_ws',ctypes.c_size_t),
                    ('active',w.DWORD),('affinity',ctypes.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
    class Counters(ctypes.Structure):
        _fields_ = [(name,ctypes.c_uint64) for name in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class Extended(ctypes.Structure):
        _fields_ = [('basic',Basic),('io',Counters),('process_memory',ctypes.c_size_t),
                    ('job_memory',ctypes.c_size_t),('peak_process',ctypes.c_size_t),('peak_job',ctypes.c_size_t)]
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p,w.LPCWSTR]
    kernel.CreateJobObjectW.restype = w.HANDLE
    kernel.SetInformationJobObject.argtypes = [w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [w.HANDLE,w.HANDLE]
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    global _job
    handle = kernel.CreateJobObjectW(None,None)
    limits = Extended()
    limits.basic.flags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    limits.process_memory = 512*1024*1024
    if not handle or not kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess()):
        if handle:
            kernel.CloseHandle(handle)
        raise ValueError('Document worker memory protection could not be enabled')
    _job = handle  # Keep the job alive until process exit.


def parse(filename, content):
    if len(content) > MAX_INPUT:
        raise ValueError('Document exceeds the supported input limit')
    ext = Path(filename).suffix.lower()
    if ext == '.docx':
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            if len(entries)>2000 or sum(item.file_size for item in entries)>80_000_000:
                raise ValueError('Document expands beyond the supported limit')
        import docx
        parts = (p.text for p in docx.Document(io.BytesIO(content)).paragraphs)
    elif ext == '.pdf':
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        if len(reader.pages)>MAX_PAGES:
            raise ValueError('PDF exceeds the supported page limit')
        parts = ((page.extract_text() or '').strip() for page in reader.pages)
    else:
        raise ValueError('Supported formats: .txt, .md, .docx, .pdf')
    output, size = [], 0
    for part in parts:
        if not part.strip():
            continue
        size += len(part.encode('utf-8'))+2
        if size>MAX_TEXT:
            raise ValueError('Extracted text exceeds the supported limit')
        output.append(part)
    return '\n\n'.join(output)


def main(args=None):
    args = sys.argv[1:] if args is None else args
    # Files avoid sys.stdin/stdout=None in the windowed PyInstaller executable.
    if len(args)!=3:
        return 2
    filename, source, target = args
    try:
        limit_memory()
        path = Path(source)
        if path.stat().st_size>MAX_INPUT:
            raise ValueError('Document exceeds the supported input limit')
        result = {'text':parse(filename,path.read_bytes())}
    except Exception as error:
        result = {'error':str(error)[:240] if isinstance(error,ValueError) else type(error).__name__}
    Path(target).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
