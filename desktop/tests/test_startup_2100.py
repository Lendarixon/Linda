import base64
import json
import re
import threading
import time

import pytest
from fastapi.testclient import TestClient

from linda_desktop import app, config, engine, i18n, updater


@pytest.mark.parametrize('system', ['en', 'ru', 'pl'])
def test_new_profile_uses_display_language(repo, monkeypatch, system):
    monkeypatch.setattr(i18n, 'system_language', lambda: system)
    assert engine.load_settings()['language'] == system
    assert engine.load_settings()['language_source'] == 'system'


@pytest.mark.parametrize('system', ['en', 'pl'])
def test_old_automatic_russian_default_migrates(repo, monkeypatch, system):
    engine.save_settings({'language': 'ru', 'preload': False, 'quality': 'lite'})
    monkeypatch.setattr(i18n, 'system_language', lambda: system)
    s = engine.load_settings()
    assert (s['language'], s['preload'], s['quality']) == (system, False, 'lite')
    app.Core()
    assert engine.load_settings()['preload'] is False


@pytest.mark.parametrize('chosen', ['en', 'ru', 'pl'])
def test_explicit_choice_survives_restart_and_system_change(repo, monkeypatch, chosen):
    monkeypatch.setattr(i18n, 'system_language', lambda: 'pl')
    client = TestClient(app.create_app(app.Core(), token='test'), headers={'x-linda-token': 'test'})
    assert client.post('/api/settings', json={'language': chosen}).status_code == 200
    monkeypatch.setattr(i18n, 'system_language', lambda: 'en')
    assert engine.load_settings()['language'] == chosen
    assert engine.load_settings()['language_source'] == 'manual'


def test_first_html_is_localized_and_does_not_trust_browser_storage(repo, monkeypatch):
    monkeypatch.setattr(i18n, 'system_language', lambda: 'pl')
    client = TestClient(app.create_app(app.Core(), token='test'))
    page = client.get('/').text
    encoded = re.search(r"atob\('([A-Za-z0-9+/=]+)'\)", page).group(1)
    boot = json.loads(base64.b64decode(encoded))
    assert boot['language'] == 'pl' and boot['version'] == '2.3.0.0'
    assert 'id="lindaStartup"' in page
    assert 'localStorage.getItem(\'linda_lang\')' not in page
    assert '__LINDA_BOOT_B64__' not in page
    assert '__STARTUP_ART__' not in page and '__STARTUP_ICON__' not in page


def test_boot_settings_cannot_inject_script(repo):
    payload = '</script><script>alert(`bad`)</script>'
    engine.save_settings({'unknown': payload})
    page = TestClient(app.create_app(app.Core(), token='test')).get('/').text
    assert payload not in page


def test_concurrent_preload_requests_warm_once_without_network_wait(repo, monkeypatch):
    core = app.Core()
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    entered, release = threading.Event(), threading.Event()
    calls = []
    def load():
        calls.append('load')
        entered.set()
        assert release.wait(3)
        core.engine.dets = {'fake': True}
        return core.engine.dets
    monkeypatch.setattr(core.engine, 'ensure_loaded', load)
    monkeypatch.setattr(core.engine, '_load_voters', lambda d: calls.append('voters'))
    monkeypatch.setattr(core.engine, 'warm_all', lambda lang: calls.append('warm'))
    core.first_check_pending = True
    assert core.preload()
    assert entered.wait(1), 'local warmup must not wait for update server'
    assert core.preloading and core.startup['phase'] == 'loading'
    assert not core.preload()
    release.set()
    for _ in range(100):
        if not core.preloading:
            break
        time.sleep(.01)
    assert calls == ['load', 'voters', 'warm']
    assert core.startup['phase'] == 'ready'


def test_failed_warmup_is_not_reported_ready(repo, monkeypatch):
    core = app.Core()
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    monkeypatch.setattr(core.engine, 'ensure_loaded', lambda: {})
    monkeypatch.setattr(core.engine, '_load_voters', lambda d: None)
    def broken(lang):
        raise RuntimeError('synthetic warmup error')
    monkeypatch.setattr(core.engine, 'warm_all', broken)
    assert core.preload()
    for _ in range(100):
        if not core.preloading:
            break
        time.sleep(.01)
    assert core.startup['phase'] == core.engine.state['phase'] == 'error'
    assert 'synthetic' in core.startup['error']


def test_no_models_or_disabled_preload_skips_splash(repo, monkeypatch):
    core = app.Core()
    monkeypatch.setattr(updater, 'is_complete', lambda: False)
    assert not core.preload()
    assert core.startup['phase'] == 'skipped'


def test_installer_explicit_language_is_used_on_first_launch(repo, monkeypatch):
    monkeypatch.setattr(i18n, 'system_language', lambda: 'ru')
    (config.data_dir() / 'installer_choice.json').write_text('{"language":"en","model_sets":["lite"]}')
    assert engine.load_settings()['language'] == 'en'
    assert engine.load_settings()['language_source'] == 'manual'


def test_both_model_tiers_are_warmed_once(monkeypatch):
    from types import SimpleNamespace
    seen = []
    pool = SimpleNamespace(get=lambda k: SimpleNamespace(margins=lambda x: seen.append(k)))
    det = lambda keys: SimpleNamespace(routed=True, pool=pool, tier=lambda lang: {'voters':keys})
    e = engine.Engine()
    monkeypatch.setattr(e, 'ensure_for_language', lambda lang: {
        'sensitive':det(['essay_m','multi_m','stylo_d']),
        'alt_sensitive':det(['speed_s','stylo_d'])})
    e.warm_all()
    assert seen == ['essay_m','multi_m','speed_s']


def test_installer_language_configuration():
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / 'installer/linda.iss').read_text(encoding='utf-8')
    assert 'UsePreviousLanguage=no' in text
    assert 'LanguageDetectionMethod=uilanguage' in text
    assert text.index('Name: "english"') < text.index('Name: "russian"')
