"""Регрессии активного ревью Dev: обновление, сервер и границы корпоративных политик."""
import asyncio
import threading
import hashlib
import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, config, updater

TOKEN = 'review-test'

def client(core=None):
    return TestClient(app_mod.create_app(core or app_mod.Core(), token=TOKEN), headers={'x-linda-token':TOKEN})

def test_cross_origin_api_and_framing_are_blocked(repo):
    c = client()
    assert c.get('/api/status', headers={'origin':'https://attacker.invalid'}).status_code == 403
    assert c.get('/api/status', headers={'origin':'http://testserver'}).status_code == 200
    assert c.get('/api/status', headers={'x-linda-token':'wrong'}).status_code == 403
    assert c.get('/api/status', headers={'host':'attacker.invalid'}).status_code == 403
    r = c.get('/')
    assert r.headers['x-frame-options'] == 'DENY'
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']

def test_allowed_folder_cannot_escape_with_parent_segments(repo, monkeypatch, tmp_path):
    allowed = tmp_path / 'allowed'
    allowed.mkdir()
    monkeypatch.setattr(config, 'enterprise', lambda:{'allowed_dirs':[str(allowed)]})
    assert config.enterprise_allows_path(str(allowed / 'sub'))
    assert not config.enterprise_allows_path(str(allowed / '..' / 'private'))
    assert not config.enterprise_allows_path(str(tmp_path / 'allowed-other'))

def test_download_reserved_before_thread_can_start(repo, monkeypatch):
    core = app_mod.Core()
    core.manifest = {'installer':{'version':'99.0.0','size':100}}
    core.update = {'app_new':True}
    c = client(core)
    class DelayedThread:
        def __init__(self, **kw): pass
        def start(self): pass
    monkeypatch.setattr(app_mod.threading, 'Thread', DelayedThread)
    assert c.post('/api/app/update').status_code == 200
    assert c.post('/api/app/update').status_code == 409
    assert core.installer_job['phase'] == 'downloading'

def test_dev_never_runs_production_installer(repo, monkeypatch):
    monkeypatch.setenv('LINDA_DEV','1')
    assert client().post('/api/app/restart').status_code == 409


def test_precise_subset_returns_localized_bad_request_without_inference(repo, monkeypatch):
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    core.engine.run = lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not infer'))
    c = client(core)
    for models in (['linda_essay'], ['linda_essay','linda_multi_v2'], ['stylo7c','stylo7c']):
        response = c.post('/api/detect', json={'text':'word '*70,'mode':'precise','models':models,'save':False})
        assert response.status_code == 400
        assert 'err_precise_requires_ensemble' not in response.text

def test_installer_flags_are_invisible_and_do_not_reboot(repo, monkeypatch):
    commands = []
    class Process:
        pid = 1
    monkeypatch.setattr(app_mod.subprocess, 'Popen', lambda cmd, **kwargs: commands.append(cmd) or Process())
    app_mod.launch_installer(Path('C:/test/Linda-Setup.exe'))
    import base64
    script = base64.b64decode(commands[0][-1]).decode('utf-16le')
    assert '/VERYSILENT' in script and '/NORESTART' in script
    assert '/RELAUNCH=1' in script and 'Wait-Process' in script
    assert '$setup.WaitForExit()' in script and '-PassThru -Wait' not in script
    assert 'INSTALLER_FAILED' in script and 'update_failure.json' in script
    assert '/FORCECLOSEAPPLICATIONS' not in script

def test_upload_parsing_does_not_block_status(repo, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    def slow_extract(*args):
        entered.set()
        assert release.wait(3)
        return 'test document'
    monkeypatch.setattr(app_mod, 'extract', slow_extract)
    api = app_mod.create_app(app_mod.Core(), token=TOKEN)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url='http://testserver', headers={'x-linda-token':TOKEN}) as c:
            upload = asyncio.create_task(c.post('/api/upload',files={'file':('test.txt',b'test')}))
            try:
                assert await asyncio.to_thread(entered.wait, 2)
                r = await asyncio.wait_for(c.get('/api/status'), timeout=1)
                assert r.status_code == 200
            finally:
                release.set()
            assert (await upload).status_code == 200
    asyncio.run(run())

def test_oversized_upload_not_parsed(repo, monkeypatch):
    monkeypatch.setattr(app_mod,'MAX_UPLOAD',32)
    monkeypatch.setattr(app_mod,'extract',lambda *a: (_ for _ in ()).throw(AssertionError('must not parse')))
    assert client().post('/api/upload',files={'file':('large.txt',b'x'*33)}).status_code == 413

def test_machine_policy_cannot_be_weakened_by_user(repo, monkeypatch, tmp_path):
    machine = tmp_path / 'machine'
    machine.mkdir()
    monkeypatch.setenv('LINDA_PROGRAMDATA', str(machine))
    (machine / 'enterprise.json').write_text(json.dumps({'disable_export':True,'require_license':True}))
    (config.data_dir() / 'enterprise.json').write_text(json.dumps({'disable_export':False,'require_license':False}))
    pol = config.enterprise()
    assert pol['disable_export'] is True and pol['require_license'] is True
    assert client().post('/api/report',json={}).status_code == 403

def test_update_rolls_back_new_changed_and_deleted_files(repo, monkeypatch):
    root = config.data_dir()
    (root / 'models').mkdir()
    (root / 'models/changed.bin').write_bytes(b'old')
    (root / 'models/stale.bin').write_bytes(b'stale')
    (root / 'manifest.json').write_bytes(b'old manifest')
    staging = root / 'staging' / '99.0.0'
    data = {'models/changed.bin':b'new','models/added.bin':b'added'}
    files = []
    for rel, content in data.items():
        dst = staging / rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(content)
        files.append({'path':rel,'size':len(content),'sha256':hashlib.sha256(content).hexdigest()})
    manifest = {'schema':1,'version':'99.0.0','files':files}
    replace = updater.os.replace
    def fail_manifest(src,dst):
        if Path(dst).name == 'manifest.json':
            raise PermissionError('simulated antivirus lock')
        return replace(src,dst)
    monkeypatch.setattr(updater.os,'replace',fail_manifest)
    import pytest
    with pytest.raises(PermissionError):
        updater._apply_staged(manifest,staging,root)
    assert (root / 'models/changed.bin').read_bytes() == b'old'
    assert (root / 'models/stale.bin').read_bytes() == b'stale'
    assert not (root / 'models/added.bin').exists()
    assert (root / 'manifest.json').read_bytes() == b'old manifest'

def test_staged_installer_rechecked_before_execution(repo, monkeypatch):
    monkeypatch.setenv('LINDA_ALLOW_HTTP','1')
    content = b'MZ' + b'original'
    (repo.root / 'installer.exe').write_bytes(content)
    info = {'url':repo.url+'/installer.exe','sha256':hashlib.sha256(content).hexdigest(),'size':len(content),'version':'99.0.0'}
    repo.publish({},'99.0.0',installer=info)
    manifest, raw = updater.get_manifest()
    p = updater.download_installer(info,version='99.0.0',manifest_raw=raw,signature=manifest['_signature'])
    st = updater.staged_installer()
    assert st
    updater.verify_staged_installer(st)
    p.write_bytes(b'MZ' + b'tampered')
    marker = p.parent / updater.INSTALLER_READY_NAME
    meta = json.loads(marker.read_text())
    meta['sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
    marker.write_text(json.dumps(meta))
    import pytest
    with pytest.raises(updater.UpdateError,match='checksum'):
        updater.verify_staged_installer(st)

def test_unsigned_pending_models_not_applied(repo):
    staging = config.data_dir() / 'staging' / '99.0.0'
    staging.mkdir(parents=True)
    (staging / 'READY').write_text('{}')
    (staging / 'manifest.json').write_text(json.dumps({'schema':1,'version':'99.0.0','files':[]}))
    result = updater.apply_pending()
    assert result['error'] and result['version'] is None

def test_required_license_enforced_for_folder_batch(repo, monkeypatch, tmp_path):
    monkeypatch.setattr(updater,'is_complete',lambda:True)
    monkeypatch.setattr(config,'enterprise',lambda:{'require_license':True,'allowed_dirs':[]})
    monkeypatch.setattr(app_mod.licensing,'public_state',lambda:{'licensed':False})
    assert client().post('/api/batch_folder',json={'path':str(tmp_path)}).status_code == 403

def test_folder_batch_can_be_cancelled_and_duplicate_is_rejected(repo, monkeypatch, tmp_path):
    from linda_pro.voters import Cancelled
    monkeypatch.setattr(updater,'is_complete',lambda:True)
    (tmp_path / 'one.txt').write_text('word '*30)
    started = threading.Event()
    core = app_mod.Core()
    def slow_run(text,mode,models,**kwargs):
        started.set()
        assert kwargs['cancel'].wait(3)
        raise Cancelled()
    monkeypatch.setattr(core.engine,'run',slow_run)
    c = client(core)
    result = {}
    thread = threading.Thread(target=lambda:result.update(response=c.post('/api/batch_folder',json={'path':str(tmp_path)})))
    thread.start()
    try:
        assert started.wait(2)
        assert c.post('/api/batch_folder',json={'path':str(tmp_path)}).status_code == 409
        assert c.post('/api/batch_folder/cancel').status_code == 200
        thread.join(3)
        assert not thread.is_alive()
        assert result['response'].json()['status'] == 'cancelled'
    finally:
        core.folder_cancel.set()
        thread.join(3)

def test_docx_expansion_limit_precedes_document_parser(monkeypatch):
    import io
    import zipfile
    import pytest
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for i in range(2001):
            archive.writestr(str(i), b'')
    with pytest.raises(ValueError, match='expands'):
        app_mod.extract('oversized.docx', buffer.getvalue())

def test_staging_parent_version_is_rejected(tmp_path):
    import pytest
    with pytest.raises(updater.UpdateError):
        updater.staging_dir('..', tmp_path)

def test_cancel_update_while_waiting_for_engine_lock_releases_waiter():
    lock = threading.Lock()
    lock.acquire()
    cancel = threading.Event()
    result = []
    def worker():
        try:
            with updater._apply_guard(lock, cancel):
                result.append('applied')
        except updater._Cancelled:
            result.append('cancelled')
    thread = threading.Thread(target=worker)
    thread.start()
    cancel.set()
    thread.join(2)
    try:
        assert result == ['cancelled'] and not thread.is_alive()
        assert lock.locked()
    finally:
        lock.release()

def test_batch_stop_cancels_active_model_job_without_touching_single(repo, monkeypatch):
    from linda_pro import voters
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    started = threading.Event()
    def run_locked(*args):
        started.set()
        assert core.batch_cancel.wait(3)
        voters.check_cancel()
    monkeypatch.setattr(core.engine, '_run_locked', run_locked)
    c = client(core)
    c.post('/api/batch/start')
    result = {}
    thread = threading.Thread(target=lambda: result.update(response=c.post('/api/detect', json={'text':'word '*30,'batch':True})))
    thread.start()
    try:
        assert started.wait(2)
        assert c.post('/api/detect/cancel').json()['cancelled'] == 0
        assert c.post('/api/batch/cancel').status_code == 200
        thread.join(3)
        assert result['response'].status_code == 409
        assert result['response'].json()['detail'] == 'cancelled'
    finally:
        core.batch_cancel.set()
        thread.join(3)

def test_csv_text_cannot_be_interpreted_as_spreadsheet_formula():
    import csv
    import io
    from linda_desktop import report
    text = '=HYPERLINK("https://example.invalid", "test")'
    result = report.to_csv({'title':'  +SUM(1,2)', 'sentences':[{'n':1,'label':'human','p_ai':.1,'text':text}]})
    rows = list(csv.reader(io.StringIO(result.lstrip('\ufeff'))))
    assert next(row[1] for row in rows if row and row[0]=='title').startswith("'")
    assert rows[-1][-1] == "'" + text
    assert rows[-1][-2] == '0.1'

def test_disconnected_detect_client_stops_worker_and_does_not_save(repo, monkeypatch):
    from starlette.requests import Request
    from linda_pro import voters
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    started = threading.Event()
    def run_locked(*args):
        started.set()
        import time
        for _ in range(100):
            voters.check_cancel()
            time.sleep(.01)
        raise AssertionError('disconnected job was not cancelled')
    async def disconnected(request):
        return started.is_set()
    monkeypatch.setattr(core.engine, '_run_locked', run_locked)
    monkeypatch.setattr(Request, 'is_disconnected', disconnected)
    monkeypatch.setattr(app_mod.history, 'add', lambda *a, **k: (_ for _ in ()).throw(AssertionError('must not save')))
    c = client(core)
    response = c.post('/api/detect', json={'text':'word '*30,'supersede':True})
    assert response.status_code == 409
    assert response.json()['detail'] == 'cancelled'
