import threading
from fastapi.testclient import TestClient
from linda_desktop import app as app_mod, updater
from linda_pro.voters import Cancelled


def test_cancel_before_job_registration_prevents_work_and_history(repo, monkeypatch):
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    monkeypatch.setattr(core.engine, 'run', lambda *a, **k: (_ for _ in ()).throw(AssertionError('cancelled work started')))
    monkeypatch.setattr(app_mod.history, 'add', lambda *a, **k: (_ for _ in ()).throw(AssertionError('cancelled work saved')))
    with TestClient(app_mod.create_app(core, token='test')) as client:
        client.headers['x-linda-token'] = 'test'
        assert client.post('/api/detect/cancel', json={'job_id':'job-A'}).json()['cancelled'] == 0
        response = client.post('/api/detect', json={'text':'word '*30, 'job_id':'job-A', 'client_id':'tab-A', 'supersede':True})
        assert response.status_code == 409 and response.json()['detail'] == 'cancelled'
        assert not core.active_checks


def test_cancel_one_tab_leaves_other_tab_running_and_can_retry(repo, monkeypatch):
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    entered = {name: threading.Event() for name in ('first', 'second')}
    release = threading.Event()
    def run(text, mode, models, cancellable=False, cancel=None):
        entered[text.split()[0]].set()
        if text.startswith('first'):
            assert cancel.wait(3)
            raise Cancelled()
        assert release.wait(3)
        assert not cancel.is_set(), 'cancellation leaked into another tab'
        return {'verdict':'human','p_ai':.1,'sentences':[]}
    monkeypatch.setattr(core.engine, 'run', run)
    results = {}
    with TestClient(app_mod.create_app(core, token='test')) as client:
        client.headers['x-linda-token'] = 'test'
        def submit(name):
            results[name] = client.post('/api/detect', json={'text':(name+' ')*30, 'job_id':'job-'+name, 'client_id':'tab-'+name, 'supersede':True, 'save':False})
        threads = [threading.Thread(target=submit, args=(name,)) for name in entered]
        for thread in threads:
            thread.start()
        try:
            assert all(event.wait(2) for event in entered.values())
            assert client.post('/api/detect/cancel', json={'job_id':'job-first'}).json()['cancelled'] == 1
            release.set()
            for thread in threads:
                thread.join(3)
            assert results['first'].status_code == 409
            assert results['second'].status_code == 200
            assert not core.active_checks
            # A new UUID after reload is independent of the cancelled UUID.
            retry = client.post('/api/detect', json={'text':'second '*30,'job_id':'retry','client_id':'tab-first','supersede':True,'save':False})
            assert retry.status_code == 200
        finally:
            release.set()
            for _, event in core.active_checks.values():
                event.set()
            for thread in threads:
                thread.join(3)


def test_malformed_check_id_is_rejected(repo):
    with TestClient(app_mod.create_app(token='test')) as client:
        client.headers['x-linda-token'] = 'test'
        assert client.post('/api/detect/cancel', json={'job_id':'../bad'}).status_code == 400
        assert client.post('/api/detect', json={'text':'word '*30,'job_id':'x','client_id':None}).status_code == 400
