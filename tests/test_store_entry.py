"""Store entry refusal must happen before core/main imports or profile writes."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

def load_entry():
    path = Path(__file__).resolve().parents[1] / 'run_store.py'
    spec = importlib.util.spec_from_file_location('test_linda_store_entry',path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def test_unpacked_entry_returns_code_before_main_import_or_profile(tmp_path,monkeypatch):
    from linda_desktop import config
    monkeypatch.setattr(config,'is_store_package',lambda:False)
    monkeypatch.setattr(config,'data_dir',lambda:(_ for _ in ()).throw(AssertionError('profile touched')))
    monkeypatch.setitem(sys.modules,'linda_desktop.__main__',None)
    monkeypatch.setenv('LINDA_HOME',str(tmp_path / 'must-not-exist'))
    assert load_entry().main([]) == 2
    assert not (tmp_path / 'must-not-exist').exists()

def test_identity_error_fails_closed_without_main(monkeypatch):
    from linda_desktop import config
    def broken():
        raise RuntimeError('identity unavailable')
    monkeypatch.setattr(config,'is_store_package',broken)
    monkeypatch.setitem(sys.modules,'linda_desktop.__main__',None)
    assert load_entry().main([]) == 2

def test_packaged_entry_rejects_legacy_profile_override(tmp_path,monkeypatch):
    from linda_desktop import config
    monkeypatch.setattr(config,'is_store_package',lambda:True)
    monkeypatch.setattr(config,'APP_NAME','Linda-Pro')
    monkeypatch.setattr(config,'data_dir',lambda:(_ for _ in ()).throw(AssertionError('profile touched')))
    monkeypatch.setitem(sys.modules,'linda_desktop.__main__',None)
    monkeypatch.setenv('LINDA_HOME',str(tmp_path / 'must-not-exist'))
    assert load_entry().main([]) == 2
    assert not (tmp_path / 'must-not-exist').exists()

def test_packaged_entry_calls_stub_main_without_injecting_profile(monkeypatch):
    from linda_desktop import config
    monkeypatch.setattr(config,'is_store_package',lambda:True)
    monkeypatch.setattr(config,'APP_NAME','Linda-Pro')
    monkeypatch.delenv('LINDA_HOME',raising=False)
    monkeypatch.delenv('LINDA_DEV',raising=False)
    for key in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):
        monkeypatch.setenv(key,'1')
    calls = []
    monkeypatch.setitem(sys.modules,'linda_desktop.__main__',SimpleNamespace(main=lambda args:calls.append(args) or 17))
    assert load_entry().main(['test-argument']) == 17
    assert calls == [['test-argument']]
    assert 'LINDA_HOME' not in __import__('os').environ
