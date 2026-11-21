"""Starting a replacement check must cancel its tab only, including queues."""
import threading

from fastapi.testclient import TestClient

from linda_desktop import app as app_mod, updater
from linda_pro.voters import Cancelled


def test_tracked_supersede_cancels_previous_tab_check_only(repo, monkeypatch):
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    core = app_mod.Core()
    entered = {name: threading.Event() for name in ('old', 'other')}
    release = threading.Event()
    events = {}
    results = {}

    def no_global_cancel():
        raise AssertionError('tracked supersede must not cancel all engine jobs')

    def run(text, mode, models, cancellable=False, cancel=None, progress=None):
        name = text.split()[0]
        events[name] = cancel
        if name == 'old':
            entered[name].set()
            assert cancel.wait(6), 'replacement did not cancel its own old check'
            raise Cancelled()
        if name == 'other':
            entered[name].set()
            assert release.wait(6)
            assert not cancel.is_set(), 'replacement cancelled another tab'
        return {'verdict': 'human', 'p_ai': .1, 'sentences': []}

    monkeypatch.setattr(core.engine, 'run', run)
    monkeypatch.setattr(core.engine, 'cancel_cancellable', no_global_cancel)
    with TestClient(app_mod.create_app(core, token='test')) as client:
        client.headers['x-linda-token'] = 'test'

        def submit(name, owner):
            results[name] = client.post('/api/detect', json={
                'text': (name + ' ') * 30, 'job_id': 'job-' + name,
                'client_id': owner, 'supersede': True, 'save': False,
            })

        threads = [threading.Thread(target=submit, args=(name, owner))
                   for name, owner in [('old', 'tab-A'), ('other', 'tab-B')]]
        for thread in threads:
            thread.start()
        try:
            assert all(event.wait(3) for event in entered.values())
            submit('new', 'tab-A')
            assert results['new'].status_code == 200
            assert events['old'].is_set()
            assert not events['other'].is_set()
            release.set()
            for thread in threads:
                thread.join(6)
            assert results['old'].status_code == 409
            assert results['other'].status_code == 200
            assert not core.active_checks
            assert core.active_requests == 0
        finally:
            release.set()
            for event in events.values():
                event.set()
            for thread in threads:
                thread.join(6)
