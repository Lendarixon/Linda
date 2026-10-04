"""Fail-closed Windows LPAC launcher. No network capabilities or inherited handles.

Only a disposable trusted runtime gets read/execute ACLs; only scratch gets write.
The parent owns a kill-on-close job before the suspended worker is resumed.
"""
import ctypes
from contextlib import contextmanager
from ctypes import wintypes as w
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile

_SPOOL_KIND = 'linda-document-job-v1'


def _write_marker(marker, info):
    temporary = marker.with_suffix('.new')
    temporary.write_text(json.dumps(info),encoding='utf-8')
    os.replace(temporary,marker)


def _delete_container(name):
    """Delete one exact owned profile, never enumerate AppContainer identities."""
    api = ctypes.WinDLL('userenv', use_last_error=True).DeleteAppContainerProfile
    api.argtypes, api.restype = [w.LPCWSTR], ctypes.c_long
    status = api(name) & 0xffffffff
    return status in (0, 0x80070002, 0x80070003, 0x80070490)


def _owned_marker(scratch):
    marker = Path(scratch).parent / 'owner.json'
    try:
        if _reparse(marker) or marker.stat().st_size > 4096:
            return None, None
        info = json.loads(marker.read_text(encoding='utf-8'))
        nonce = marker.parent.name
        if info.get('kind') != _SPOOL_KIND or info.get('nonce') != nonce or info.get('pid') != os.getpid():
            return None, None
        if len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
            return None, None
        return marker, info
    except (OSError, ValueError, TypeError, AttributeError):
        return None, None


def _reparse(path):
    """Reject junctions as well as symlinks; never follow a cleanup target."""
    try:
        value = Path(path).lstat()
        return bool(getattr(value, 'st_file_attributes', 0) & 0x400) or Path(path).is_symlink()
    except OSError:
        return True


def _dead(pid):
    if not isinstance(pid, int) or pid < 1:
        return False
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except OSError:
            pass
        return False
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE, w.DWORD]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.OpenProcess(0x100000, False, pid)
    if not handle:
        return ctypes.get_last_error() == 87  # nonexistent PID; access denied is unknown
    try:
        return kernel.WaitForSingleObject(handle, 0) == 0
    finally:
        kernel.CloseHandle(handle)


def _remove_owned_job(root, job):
    root, job = Path(root), Path(job)
    if _reparse(root) or _reparse(job) or job.parent.resolve() != root.resolve():
        return False
    resolved = root.resolve()
    # Worker is already dead (or never started); no descendant can create links now.
    for current, dirs, files in os.walk(job, followlinks=False):
        for name in dirs + files:
            path = Path(current) / name
            if _reparse(path) or not path.resolve().is_relative_to(resolved):
                return False
    if job.resolve().parent != resolved:
        return False
    shutil.rmtree(job)
    return True


def cleanup_stale(root, minimum_age=60):
    """Remove only this application's marked jobs with a proven dead broker.

    Never scans global TEMP, other profiles, unknown entries, live/unknown PIDs,
    or jobs containing reparse points. Called on the next document import.
    """
    import json
    root = Path(root)
    removed = 0
    if not root.is_dir() or _reparse(root):
        return removed
    for job in root.iterdir():
        if len(job.name) != 32 or any(c not in '0123456789abcdef' for c in job.name) or not job.is_dir() or _reparse(job):
            continue
        marker = job / 'owner.json'
        try:
            if _reparse(marker) or marker.stat().st_size > 4096:
                continue
            info = json.loads(marker.read_text(encoding='utf-8'))
            if info.get('kind') != _SPOOL_KIND or info.get('nonce') != job.name:
                continue
            created = float(info['created'])
            if not 0 < created <= time.time() - minimum_age or not _dead(info['pid']):
                continue
            container = info.get('container')
            if container is not None:
                if container != 'Linda.Document.' + job.name or not _delete_container(container):
                    continue  # Keep marker and files so exact deletion can be retried.
            removed += bool(_remove_owned_job(root, job))
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return removed


@contextmanager
def scratch_job():
    from . import config
    import json
    base = config.data_dir()
    root = base / '_document_spool'
    if _reparse(base) or root.exists() and _reparse(root):
        raise ValueError('Document spool must be a normal application directory')
    root.mkdir(exist_ok=True)
    cleanup_stale(root)
    job = root / uuid.uuid4().hex
    job.mkdir()
    # Marker lives outside the worker's explicit read/write ACL grants.
    _write_marker(job/'owner.json',{'kind':_SPOOL_KIND,'nonce':job.name,'pid':os.getpid(),'created':time.time()})
    scratch = job / 'scratch'
    scratch.mkdir()
    try:
        yield scratch
    finally:
        # A failed exact AppContainer deletion retains the recovery marker.
        try:
            info = json.loads((job/'owner.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            info = {'container_pending':True}
        if not info.get('container_pending'):
            _remove_owned_job(root, job)
        else:
            # Worker handles are closed; remove plaintext while keeping identity
            # for a later exact profile-deletion retry. Reject any reparse point.
            _remove_owned_job(job, scratch)


def stage_runtime(directory):
    """Copy runtime code only; never grant access to installation/profile roots."""
    root = Path(directory)
    if getattr(sys, 'frozen', False):
        origin = Path(sys._MEIPASS) / 'assets' / 'document-parser'
        executable = origin / 'Linda-Document-Worker.exe'
        if not executable.is_file():
            raise ValueError('Secure document parser runtime is missing; reinstall the application')
        try:
            shutil.copytree(origin, root, dirs_exist_ok=True)
        except shutil.Error as error:
            # No document content is involved: stage_runtime copies trusted code.
            # Preserve the precise Windows failure locally, not in the UI response.
            import logging
            logging.getLogger(__name__).exception('Trusted document runtime staging failed')
            raise ValueError('Secure document runtime could not be staged') from error
        return [str(root / executable.name)]
    base = Path(sys.base_prefix)
    executable = root / 'python.exe'
    shutil.copy2(base / 'python.exe', executable)
    for item in base.glob('*.dll'):
        shutil.copy2(item, root / item.name)
    shutil.copytree(base / 'DLLs', root / 'DLLs')
    with zipfile.ZipFile(root / 'stdlib.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for current, dirs, files in os.walk(base / 'Lib'):
            dirs[:] = [name for name in dirs if name not in ('site-packages', '__pycache__', 'test', 'tests', 'tkinter', 'idlelib', 'ensurepip')]
            for name in files:
                if name.endswith('.py'):
                    path = Path(current) / name
                    archive.write(path, path.relative_to(base / 'Lib').as_posix())
    for name in ('docx', 'pypdf', 'lxml', 'typing_extensions'):
        spec = importlib.util.find_spec(name)
        if spec is None:
            raise ValueError('Document parser runtime is unavailable')
        origin = Path(spec.origin)
        if spec.submodule_search_locations:
            shutil.copytree(origin.parent, root / name, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(origin, root / origin.name)
    shutil.copy2(Path(__file__).with_name('document_worker.py'), root / 'worker.py')
    (root / f'python{sys.version_info.major}{sys.version_info.minor}._pth').write_text('stdlib.zip\nDLLs\n.\n', encoding='ascii')
    return [str(executable), str(root / 'worker.py')]


class Startup(ctypes.Structure):
    _fields_ = [('cb', w.DWORD), ('reserved', w.LPWSTR), ('desktop', w.LPWSTR), ('title', w.LPWSTR),
                ('x', w.DWORD), ('y', w.DWORD), ('xs', w.DWORD), ('ys', w.DWORD), ('xc', w.DWORD), ('yc', w.DWORD),
                ('fill', w.DWORD), ('flags', w.DWORD), ('show', w.WORD), ('reserved2size', w.WORD),
                ('reserved2', ctypes.c_void_p), ('stdin', w.HANDLE), ('stdout', w.HANDLE), ('stderr', w.HANDLE)]


class StartupEx(ctypes.Structure):
    _fields_ = [('startup', Startup), ('attributes', ctypes.c_void_p)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [('process', w.HANDLE), ('thread', w.HANDLE), ('pid', w.DWORD), ('tid', w.DWORD)]


class Capabilities(ctypes.Structure):
    _fields_ = [('sid', ctypes.c_void_p), ('capabilities', ctypes.c_void_p), ('count', w.DWORD), ('reserved', w.DWORD)]


class Basic(ctypes.Structure):
    _fields_ = [('process_time', ctypes.c_int64), ('job_time', ctypes.c_int64), ('flags', w.DWORD),
                ('min_ws', ctypes.c_size_t), ('max_ws', ctypes.c_size_t), ('active', w.DWORD),
                ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]


class Extended(ctypes.Structure):
    _fields_ = [('basic', Basic), ('io', ctypes.c_uint64 * 6), ('process_memory', ctypes.c_size_t),
                ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]


class SidAttribute(ctypes.Structure):
    _fields_ = [('sid', ctypes.c_void_p), ('attributes', w.DWORD)]


def _acl(path, sid, rights):
    # icacls arguments are a list, never interpreted by a shell. Only owned copies.
    completed = subprocess.run(['icacls', str(path), '/grant', f'*{sid}:(OI)(CI){rights}', '/T', '/Q'],
                               capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if completed.returncode:
        raise ValueError('Document sandbox permissions could not be enabled')
    if rights == 'M':
        completed = subprocess.run(['icacls', str(path), '/setintegritylevel', '(OI)(CI)L', '/T', '/Q'],
                                   capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if completed.returncode:
            raise ValueError('Document sandbox integrity could not be enabled')


def run(command, runtime, scratch, timeout):
    if os.name != 'nt':
        raise ValueError('Secure PDF/DOCX parsing requires Windows AppContainer')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user = ctypes.WinDLL('userenv', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    def bind(lib, name, args, result=w.BOOL):
        fn = getattr(lib, name)
        fn.argtypes, fn.restype = args, result
        return fn
    close = bind(kernel, 'CloseHandle', [w.HANDLE])
    create_profile = bind(user, 'CreateAppContainerProfile', [w.LPCWSTR, w.LPCWSTR, w.LPCWSTR, ctypes.c_void_p, w.DWORD, ctypes.POINTER(ctypes.c_void_p)], ctypes.c_long)
    free_sid = bind(advapi, 'FreeSid', [ctypes.c_void_p], ctypes.c_void_p)
    to_string = bind(advapi, 'ConvertSidToStringSidW', [ctypes.c_void_p, ctypes.POINTER(w.LPWSTR)])
    local_free = bind(kernel, 'LocalFree', [ctypes.c_void_p], ctypes.c_void_p)
    initialize = bind(kernel, 'InitializeProcThreadAttributeList', [ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_size_t)])
    update = bind(kernel, 'UpdateProcThreadAttribute', [ctypes.c_void_p, w.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p])
    delete_attrs = bind(kernel, 'DeleteProcThreadAttributeList', [ctypes.c_void_p], None)
    create_job = bind(kernel, 'CreateJobObjectW', [ctypes.c_void_p, w.LPCWSTR], w.HANDLE)
    set_job = bind(kernel, 'SetInformationJobObject', [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD])
    assign_job = bind(kernel, 'AssignProcessToJobObject', [w.HANDLE, w.HANDLE])
    create = bind(kernel, 'CreateProcessW', [w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL, w.DWORD, ctypes.c_void_p, w.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ProcessInfo)])
    resume = bind(kernel, 'ResumeThread', [w.HANDLE], w.DWORD)
    wait = bind(kernel, 'WaitForSingleObject', [w.HANDLE, w.DWORD], w.DWORD)
    terminate = bind(kernel, 'TerminateProcess', [w.HANDLE, w.UINT])
    exit_code = bind(kernel, 'GetExitCodeProcess', [w.HANDLE, ctypes.POINTER(w.DWORD)])
    derive = bind(ctypes.WinDLL('kernelbase', use_last_error=True), 'DeriveCapabilitySidsFromName', [w.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.DWORD), ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(w.DWORD)])
    group_sids, cap_sids, group_count, cap_count = ctypes.c_void_p(), ctypes.c_void_p(), w.DWORD(), w.DWORD()
    marker, ownership = _owned_marker(scratch)
    name = 'Linda.Document.' + (ownership['nonce'] if ownership else uuid.uuid4().hex)
    if marker:
        ownership.update(container=name,container_pending=True)
        _write_marker(marker,ownership)
    sid, job, attributes, info = ctypes.c_void_p(), None, None, ProcessInfo()
    try:
        if create_profile(name, name, 'Disposable document parser', None, 0, ctypes.byref(sid)) < 0:
            raise ValueError('Document sandbox profile could not be created')
        sid_string = w.LPWSTR()
        if not to_string(sid, ctypes.byref(sid_string)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            _acl(runtime, sid_string.value, 'RX')
            _acl(scratch, sid_string.value, 'M')
        finally:
            local_free(ctypes.cast(sid_string, ctypes.c_void_p))
        size = ctypes.c_size_t()
        initialize(None, 2, 0, ctypes.byref(size))
        attributes = ctypes.create_string_buffer(size.value)
        if not initialize(attributes, 2, 0, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        # Windows loader needs registryRead. No network, COM or user-file capabilities.
        if not derive('registryRead', ctypes.byref(group_sids), ctypes.byref(group_count), ctypes.byref(cap_sids), ctypes.byref(cap_count)):
            raise ctypes.WinError(ctypes.get_last_error())
        cap_array = (SidAttribute * cap_count.value)()
        pointers = ctypes.cast(cap_sids, ctypes.POINTER(ctypes.c_void_p))
        for index in range(cap_count.value):
            cap_array[index] = SidAttribute(pointers[index], 4)
        caps, policy = Capabilities(sid, ctypes.addressof(cap_array), cap_count.value, 0), w.DWORD(1)
        # LPAC: ignore broad ALL APPLICATION PACKAGES read grants.
        for kind, value in ((0x20009, caps), (0x2000f, policy)):
            if not update(attributes, 0, kind, ctypes.byref(value), ctypes.sizeof(value), None, None):
                raise ctypes.WinError(ctypes.get_last_error())
        job = create_job(None, None)
        limits = Extended()
        limits.basic.flags = 0x2000 | 0x100 | 0x8  # kill-on-close, memory, active-process count
        limits.basic.active = 1
        limits.process_memory = 512 * 1024 * 1024
        if not job or not set_job(job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        startup = StartupEx()
        startup.startup.cb, startup.attributes = ctypes.sizeof(startup), ctypes.addressof(attributes)
        env = {'SystemRoot': os.environ['SystemRoot'], 'WINDIR': os.environ['SystemRoot'],
               'USERPROFILE': str(scratch), 'LOCALAPPDATA': str(scratch), 'APPDATA': str(scratch),
               'TEMP': str(scratch), 'TMP': str(scratch), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
               'LINDA_DOCUMENT_SANDBOX': '1'}
        env_block = ctypes.create_unicode_buffer('\0'.join(f'{k}={v}' for k, v in sorted(env.items())) + '\0\0')
        line = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
        if not create(command[0], line, None, None, False, 0x80000 | 0x4 | 0x400 | 0x08000000,
                      env_block, str(scratch), ctypes.byref(startup), ctypes.byref(info)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not assign_job(job, info.process):
            raise ctypes.WinError(ctypes.get_last_error())
        if resume(info.thread) == 0xffffffff:
            raise ctypes.WinError(ctypes.get_last_error())
        result = wait(info.process, int(timeout * 1000))
        if result == 258:
            raise ValueError('Document parsing timed out')
        if result != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        code = w.DWORD()
        if not exit_code(info.process, ctypes.byref(code)) or code.value:
            raise ValueError(f'Document parser stopped unexpectedly ({code.value:#x})')
        return info.pid
    except OSError as error:
        raise ValueError(f'Document sandbox could not be enabled (Windows {error.winerror})') from None
    finally:
        if info.process:
            terminate(info.process, 1)
            wait(info.process, 5000)
        if job:
            close(job)
        for handle in (info.thread, info.process):
            if handle:
                close(handle)
        if attributes:
            delete_attrs(attributes)
        if sid:
            free_sid(sid)
        deleted = _delete_container(name)
        if marker and deleted:
            ownership['container_pending'] = False
            _write_marker(marker,ownership)
        for pointers, count in ((group_sids, group_count), (cap_sids, cap_count)):
            if pointers:
                values = ctypes.cast(pointers, ctypes.POINTER(ctypes.c_void_p))
                for index in range(count.value):
                    local_free(values[index])
                local_free(pointers)


def parse_worker(filename, source, target, timeout):
    with tempfile.TemporaryDirectory(prefix='runtime-', dir=source.parent.parent) as runtime:
        command = stage_runtime(runtime) + [filename, str(source), str(target)]
        return run(command, runtime, source.parent, timeout)
