"""Store channel must not share legacy data or invoke the EXE updater."""
import pytest
from linda_desktop import config, updater

def test_real_windows_process_is_unpacked():
    # The pytest runner is unpackaged. This exercises the actual Windows API.
    assert config.package_family_name() is None

def test_packaged_data_separate_from_legacy(tmp_path, monkeypatch):
    monkeypatch.delenv('LINDA_HOME', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(config, 'package_family_name', lambda: 'Assigned.Linda_abc123')
    assert config.data_dir() == tmp_path / 'Packages' / 'Assigned.Linda_abc123' / 'LocalState'
    assert not (tmp_path / config.APP_NAME).exists()

def test_unpacked_profile_unchanged(tmp_path, monkeypatch):
    monkeypatch.delenv('LINDA_HOME', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    monkeypatch.setattr(config, 'package_family_name', lambda: None)
    assert config.data_dir() == tmp_path / config.APP_NAME

def test_test_override_remains_explicit(tmp_path, monkeypatch):
    monkeypatch.setenv('LINDA_HOME', str(tmp_path / 'fixture'))
    monkeypatch.setattr(config, 'package_family_name', lambda: 'Assigned.Linda_abc123')
    assert config.data_dir() == tmp_path / 'fixture'

def test_store_exe_download_blocked_before_network_or_disk(tmp_path, monkeypatch):
    monkeypatch.setattr(config, 'is_store_package', lambda: True)
    with pytest.raises(updater.UpdateError, match='Microsoft Store'):
        updater.download_installer({}, root=tmp_path / 'must-not-exist')
    assert not (tmp_path / 'must-not-exist').exists()
    assert updater.staged_installer(tmp_path / 'must-not-exist') is None
    with pytest.raises(updater.UpdateError, match='EXE installers'):
        updater.verify_staged_installer({})

def test_store_models_still_independent_but_exe_not_advertised(monkeypatch):
    monkeypatch.setattr(config, 'is_store_package', lambda: True)
    monkeypatch.setattr(updater, 'installed_version', lambda: '1.0')
    monkeypatch.setattr(updater, 'is_complete', lambda: True)
    monkeypatch.setattr(updater, 'files_to_fetch', lambda m: [{'size':20}])
    manifest = {'version':'2.0', 'min_app':'99.0', 'installer':{'version':'99.0','size':50}}
    result = updater.update_status(manifest)
    assert result['weights_update'] is True
    assert result['bytes_to_download'] == 20
    assert result['app_required'] is True
    assert result['app_new'] is False and result['installer'] is None
    assert result['distribution'] == 'store'
    assert manifest['installer']['version'] == '99.0'  # signed manifest not mutated

def test_store_http_install_routes_block_before_core_work(monkeypatch):
    from fastapi.testclient import TestClient
    from linda_desktop import app
    monkeypatch.setattr(config, 'is_store_package', lambda: True)
    # Any unguarded state access fails: no core engine, jobs, or staging available.
    client = TestClient(app.create_app(object(),token='fixture-store-token'),
                        headers={'x-linda-token':'fixture-store-token'})
    for path in ('/api/app/update','/api/app/restart'):
        response = client.post(path)
        assert response.status_code == 409
        assert 'Microsoft Store' in response.text

def test_store_launcher_blocked_before_subprocess(tmp_path, monkeypatch):
    from linda_desktop import app
    monkeypatch.setattr(config, 'is_store_package', lambda: True)
    with pytest.raises(RuntimeError, match='Microsoft Store'):
        app.launch_installer(tmp_path / 'not-created.exe')
    assert not (tmp_path / 'not-created.exe').exists()
