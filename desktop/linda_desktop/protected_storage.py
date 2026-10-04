"""Current-user Windows DPAPI protection; fail closed on unsupported platforms."""
import ctypes
import hashlib
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

MAGIC = b'LINDA-DPAPI-1\n'


def _crypt(data: bytes, purpose: str, decrypt: bool) -> bytes:
    if os.name != 'nt':
        raise RuntimeError('Protected local storage requires Windows DPAPI')
    from ctypes import wintypes as w
    class Blob(ctypes.Structure):
        _fields_ = [('size',w.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
    def blob(value):
        buffer=ctypes.create_string_buffer(value)
        return Blob(len(value),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte))),buffer
    source,source_buffer=blob(data)
    entropy,entropy_buffer=blob(('Linda-Pro/storage/v1/'+purpose).encode('utf-8'))
    output=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    kernel.LocalFree.restype=ctypes.c_void_p
    if decrypt:
        fn=crypt.CryptUnprotectData
        fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,w.DWORD,ctypes.POINTER(Blob)]
        args=(ctypes.byref(source),None,ctypes.byref(entropy),None,None,1,ctypes.byref(output))
    else:
        fn=crypt.CryptProtectData
        fn.argtypes=[ctypes.POINTER(Blob),w.LPCWSTR,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,w.DWORD,ctypes.POINTER(Blob)]
        # UI forbidden, USER scope; never CRYPTPROTECT_LOCAL_MACHINE.
        args=(ctypes.byref(source),'Linda-Pro protected local data',ctypes.byref(entropy),None,None,1,ctypes.byref(output))
    fn.restype=w.BOOL
    if not fn(*args):
        raise ValueError('Protected data is damaged or unavailable to this Windows account')
    try:
        return ctypes.string_at(output.data,output.size)
    finally:
        if output.data:
            ctypes.memset(output.data,0,output.size)
            kernel.LocalFree(output.data)


def protect(data: bytes, purpose: str='storage') -> bytes:
    return MAGIC+_crypt(data,purpose,False)


def unprotect(data: bytes, purpose: str='storage') -> bytes:
    if not data.startswith(MAGIC):
        raise ValueError('Unknown protected data format')
    return _crypt(data[len(MAGIC):],purpose,True)


def atomic_write(path: Path, data: bytes):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    descriptor,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.protected-tmp',dir=path.parent)
    try:
        with os.fdopen(descriptor,'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def storage_lock(path: Path):
    """Serialize snapshot transactions across processes of the same Windows user."""
    if os.name!='nt':
        raise RuntimeError('Protected local storage requires Windows')
    from ctypes import wintypes as w
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,w.BOOL,w.LPCWSTR]
    kernel.CreateMutexW.restype=w.HANDLE
    kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
    kernel.ReleaseMutex.argtypes=[w.HANDLE]
    kernel.CloseHandle.argtypes=[w.HANDLE]
    name='Local\\LindaStorage-'+hashlib.sha256(str(Path(path).resolve()).casefold().encode()).hexdigest()
    handle=kernel.CreateMutexW(None,False,name)
    if not handle:
        raise RuntimeError('Protected storage lock unavailable')
    acquired=False
    try:
        status=kernel.WaitForSingleObject(handle,30_000)
        if status not in (0,0x80):
            raise RuntimeError('Protected storage is busy')
        acquired=True
        yield
    finally:
        if acquired: kernel.ReleaseMutex(handle)
        kernel.CloseHandle(handle)
