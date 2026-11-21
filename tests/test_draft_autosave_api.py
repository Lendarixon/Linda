import threading
from types import SimpleNamespace
from fastapi.testclient import TestClient
from linda_desktop import app,config,protected_storage,restart_draft

def test_encrypted_autosave_rejects_older_revision_and_survives_resume(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path)
    monkeypatch.setattr(restart_draft,'allowed',lambda:True)
    client=TestClient(app.create_app(SimpleNamespace(settings_lock=threading.Lock()),token='synthetic-token'),headers={'x-linda-token':'synthetic-token'})
    def save(text,revision):
        return client.post('/api/draft/save',json={'client_id':'synthetic-client','revision':revision,'text':text})
    assert save('NEW_SYNTHETIC_PRIVATE_TEXT',2).json()['status']=='ok'
    stored=(tmp_path/'restart-draft.json').read_bytes()
    assert stored.startswith(protected_storage.MAGIC) and b'PRIVATE_TEXT' not in stored
    assert save('OLDER_SYNTHETIC_TEXT',1).json()['status']=='stale'
    assert (tmp_path/'restart-draft.json').read_bytes()==stored
    assert client.get('/api/draft/resume').json()['draft']['text']=='NEW_SYNTHETIC_PRIVATE_TEXT'
    assert client.post('/api/draft/save',json={'client_id':'x','revision':True,'text':'invalid'}).status_code==400
    monkeypatch.setattr(restart_draft,'allowed',lambda:False)
    assert save('DISALLOWED_TEXT',3).status_code==403
    assert (tmp_path/'restart-draft.json').read_bytes()==stored

def test_browser_drafts_do_not_persist_plaintext_to_session_storage():
    from pathlib import Path
    html=(Path(__file__).resolve().parents[1]/'web/index.html').read_text(encoding='utf-8')
    assert "sessionStorage.setItem('linda-draft'" not in html
