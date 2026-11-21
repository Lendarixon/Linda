"""Real Windows denial tests against synthetic files, no user documents."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import pytest
from linda_desktop import document_sandbox as sandbox

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows LPAC security boundary')


@pytest.fixture(autouse=True)
def isolated_document_spool(monkeypatch,tmp_path):
    monkeypatch.setenv('LINDA_HOME',str(tmp_path/'document-profile'))


def test_stale_cleanup_only_proven_dead_owned_jobs(tmp_path,monkeypatch):
    root = tmp_path/'spool'; root.mkdir()
    def job(name,pid):
        directory=root/name; directory.mkdir()
        (directory/'owner.json').write_text(json.dumps({'kind':sandbox._SPOOL_KIND,'nonce':name,'pid':pid,'created':time.time()-120}))
        (directory/'synthetic-input').write_text('private synthetic')
        return directory
    dead=job('a'*32,11111)
    live=job('b'*32,22222)
    unknown=root/'unmarked'; unknown.mkdir(); (unknown/'text').write_text('keep')
    monkeypatch.setattr(sandbox,'_dead',lambda pid:pid == 11111)
    assert sandbox.cleanup_stale(root) == 1
    assert not dead.exists() and live.exists() and unknown.exists()


def test_stale_cleanup_deletes_only_exact_owned_container_and_retains_failed(tmp_path,monkeypatch):
    root=tmp_path/'spool'; root.mkdir()
    deleted=[]
    def job(letter,pid,container):
        directory=root/(letter*32); directory.mkdir()
        (directory/'owner.json').write_text(json.dumps({'kind':sandbox._SPOOL_KIND,'nonce':directory.name,'pid':pid,'created':time.time()-120,'container':container,'container_pending':True}))
        (directory/'input').write_text('synthetic')
        return directory
    exact=job('a',11111,'Linda.Document.'+'a'*32)
    live=job('b',22222,'Linda.Document.'+'b'*32)
    foreign=job('c',11111,'Other.Application.'+'c'*32)
    wrong_nonce=job('d',11111,'Linda.Document.'+'e'*32)
    failed=job('f',11111,'Linda.Document.'+'f'*32)
    monkeypatch.setattr(sandbox,'_dead',lambda pid:pid==11111)
    def remove(name):
        deleted.append(name)
        return name != 'Linda.Document.'+'f'*32
    monkeypatch.setattr(sandbox,'_delete_container',remove)
    assert sandbox.cleanup_stale(root)==1
    assert not exact.exists()
    assert all(directory.exists() for directory in (live,foreign,wrong_nonce,failed))
    assert sorted(deleted)==['Linda.Document.'+'a'*32,'Linda.Document.'+'f'*32]


def test_cleanup_refuses_recent_marker_and_reparse(tmp_path,monkeypatch):
    root=tmp_path/'spool'; root.mkdir()
    job=root/('a'*32); job.mkdir()
    (job/'owner.json').write_text(json.dumps({'kind':sandbox._SPOOL_KIND,'nonce':job.name,'pid':11111,'created':time.time()}))
    monkeypatch.setattr(sandbox,'_dead',lambda pid:True)
    assert sandbox.cleanup_stale(root) == 0 and job.exists()
    monkeypatch.setattr(sandbox,'_reparse',lambda path:Path(path) == job)
    assert sandbox.cleanup_stale(root,minimum_age=0) == 0 and job.exists()


def test_marker_is_outside_worker_writable_scratch_and_normal_exit_removes(monkeypatch,tmp_path):
    with sandbox.scratch_job() as scratch:
        assert (scratch.parent/'owner.json').is_file()
        assert not (scratch/'owner.json').exists()
        (scratch/'synthetic-input').write_text('temporary synthetic')
        job=scratch.parent
    assert not job.exists()


def test_failed_profile_cleanup_keeps_identity_but_removes_plaintext():
    with sandbox.scratch_job() as scratch:
        job=scratch.parent
        marker=job/'owner.json'
        info=json.loads(marker.read_text())
        info.update(container='Linda.Document.'+job.name,container_pending=True)
        sandbox._write_marker(marker,info)
        (scratch/'input').write_text('private synthetic')
    assert job.exists() and marker.exists() and not scratch.exists()


def test_lpac_denies_outside_read_write_runtime_write_and_network(tmp_path):
    runtime, scratch = tmp_path/'runtime', tmp_path/'scratch'
    runtime.mkdir(); scratch.mkdir()
    outside = tmp_path/'outside-secret.txt'
    outside.write_text('synthetic private data', encoding='utf-8')
    command = sandbox.stage_runtime(runtime)
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0)); listener.listen()
        port = listener.getsockname()[1]
        Path(command[1]).write_text('''import json,socket,sys,subprocess
from pathlib import Path
outside,runtime,scratch,port=sys.argv[1:]
result={}
def probe(name, action):
    try:
        action(); result[name]='allowed'
    except OSError:
        result[name]='denied'
probe('outside_read',lambda:Path(outside).read_bytes())
probe('outside_write',lambda:Path(outside).write_text('changed'))
probe('outside_new',lambda:Path(outside+'-new').write_text('created'))
probe('runtime_write',lambda:Path(runtime,'injected.py').write_text('injected'))
probe('loopback',lambda:socket.create_connection(('127.0.0.1',int(port)),timeout=1).close())
probe('public_network',lambda:socket.create_connection(('1.1.1.1',443),timeout=1).close())
probe('child_process',lambda:subprocess.run([sys.executable,'-c','pass'],check=True))
probe('scratch_write',lambda:Path(scratch,'scratch-ok').write_text('ok'))
Path(scratch,'result.json').write_text(json.dumps(result))
''', encoding='utf-8')
        sandbox.run(command+[str(outside),str(runtime),str(scratch),str(port)],runtime,scratch,10)
    result = json.loads((scratch/'result.json').read_text())
    assert result == dict(outside_read='denied',outside_write='denied',outside_new='denied',runtime_write='denied',loopback='denied',public_network='denied',child_process='denied',scratch_write='allowed')
    assert outside.read_text() == 'synthetic private data'


def test_fail_closed_preserves_txt(monkeypatch):
    from linda_desktop import documents
    def fail(*args):
        raise ValueError('Document sandbox could not be enabled')
    monkeypatch.setattr(sandbox,'run',fail)
    with pytest.raises(ValueError,match='sandbox'):
        documents.extract('a.pdf',b'bad')
    assert documents.extract('a.txt',b'plain') == 'plain'


def test_parent_exit_kills_worker(tmp_path):
    import uuid
    spool=tmp_path/'_document_spool'; spool.mkdir()
    job=spool/uuid.uuid4().hex; job.mkdir()
    runtime,scratch = job/'runtime',job/'scratch'
    runtime.mkdir(); scratch.mkdir()
    command = sandbox.stage_runtime(runtime)
    Path(command[1]).write_text("import os,time; from pathlib import Path; Path('worker-pid').write_text(str(os.getpid())); time.sleep(30)",encoding='utf-8')
    script = tmp_path/'broker.py'
    script.write_text('''import json,os,sys,threading,time
from pathlib import Path
from linda_desktop.document_sandbox import run
runtime,scratch,command=sys.argv[1:]
job=Path(scratch).parent
Path(job,'owner.json').write_text(json.dumps({'kind':'linda-document-job-v1','nonce':job.name,'pid':os.getpid(),'created':time.time()}))
threading.Thread(target=run,args=(json.loads(command),runtime,Path(scratch),30),daemon=True).start()
for _ in range(100):
    if Path(scratch,'worker-pid').exists(): os._exit(0)
    time.sleep(.05)
os._exit(3)
''',encoding='utf-8')
    env = dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]))
    broker = subprocess.run([sys.executable,str(script),str(runtime),str(scratch),json.dumps(command)],env=env,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
    assert broker.returncode == 0
    pid = int((scratch/'worker-pid').read_text())
    import ctypes
    from ctypes import wintypes as w
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes = [w.DWORD,w.BOOL,w.DWORD]
    kernel.OpenProcess.restype = w.HANDLE
    kernel.WaitForSingleObject.argtypes = [w.HANDLE,w.DWORD]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.OpenProcess(0x100000,False,pid)
    if handle:
        try:
            assert kernel.WaitForSingleObject(handle,3000) == 0
        finally:
            kernel.CloseHandle(handle)
    ownership=json.loads((job/'owner.json').read_text())
    assert ownership['container'] == 'Linda.Document.'+job.name
    assert sandbox.cleanup_stale(spool,minimum_age=0) == 1
    assert not job.exists()
