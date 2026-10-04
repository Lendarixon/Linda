import json
import threading
import time
import pytest
from fastapi.testclient import TestClient
from linda_desktop import app as app_mod, config, restart_draft, protected_storage
from test_update_restart import _stage

def test_draft_roundtrip_and_stale_ack_cannot_delete_new_text(repo):
    restart_draft.save('First draft')
    old = restart_draft.read()
    restart_draft.save('New draft\nwith exact whitespace. ')
    new = restart_draft.read()
    assert new['text'] == 'New draft\nwith exact whitespace. '
    assert not restart_draft.acknowledge(old['id'])
    assert restart_draft.read()['id'] == new['id']
    assert restart_draft.acknowledge(new['id'])
    assert restart_draft.read() is None

def test_disabled_history_does_not_keep_restart_text(repo):
    restart_draft.save('Sensitive test draft')
    (config.data_dir()/'enterprise.json').write_text(json.dumps({'disable_history':True}))
    assert restart_draft.read() is None
    assert not (config.data_dir()/'restart-draft.json').exists()
    with pytest.raises(PermissionError):
        restart_draft.save('Should never be written')

def test_oversize_and_expired_drafts_are_not_restored(repo):
    with pytest.raises(ValueError):
        restart_draft.save('x'*(restart_draft.MAX_CHARS+1))
    restart_draft.save('Old text')
    path = config.data_dir()/'restart-draft.json'
    record = json.loads(protected_storage.unprotect(path.read_bytes(), 'restart-draft').decode('utf-8'))
    record['ts'] = time.time()-86401
    protected_storage.atomic_write(path, protected_storage.protect(json.dumps(record).encode('utf-8'), 'restart-draft'))
    assert restart_draft.read() is None and not path.exists()

def test_restart_draft_write_failure_keeps_app_running(repo, monkeypatch):
    _stage(config.data_dir(),'99.0.0',repo=repo)
    core = app_mod.Core()
    monkeypatch.setattr(restart_draft,'save',lambda text: (_ for _ in ()).throw(OSError('disk full')))
    launched=[]
    monkeypatch.setattr(app_mod,'launch_installer',lambda path: launched.append(path))
    with TestClient(app_mod.create_app(core,token='test')) as client:
        client.headers['x-linda-token']='test'
        response = client.post('/api/app/restart',json={'draft':'unsaved work'})
        assert response.status_code == 400
        assert core.installer_job['phase'] != 'launching' and not launched

def test_restart_draft_api_ack_is_audited_without_text(repo):
    restart_draft.save('Synthetic document')
    with TestClient(app_mod.create_app(token='test')) as client:
        client.headers['x-linda-token']='test'
        record = client.get('/api/draft/resume').json()['draft']
        assert record['text'] == 'Synthetic document'
        assert client.post('/api/draft/ack',json={'id':record['id']}).json()['restored']
        entries = client.get('/api/audit',params={'action':'draft_restore'}).json()['items']
        assert entries[0]['detail'] == record['id']
        assert client.get('/api/draft/resume').json()['draft'] is None

def test_queued_request_blocks_restart_and_launching_blocks_new_work(repo):
    _stage(config.data_dir(),'99.0.0',repo=repo)
    core = app_mod.Core()
    with TestClient(app_mod.create_app(core,token='test')) as client:
        client.headers['x-linda-token']='test'
        core.active_requests=1
        assert client.post('/api/app/restart').status_code == 409
        core.active_requests=0
        core.installer_job['phase']='launching'
        assert client.post('/api/detect',json={'text':'word '*30}).status_code == 409
        assert client.post('/api/upload',files={'file':('text.txt',b'word '*30)}).status_code == 409
        assert client.post('/api/batch_folder',json={'path':str(config.data_dir())}).status_code == 409
        assert core.active_requests == 0
