import sqlite3
import os
import subprocess
import sys
from pathlib import Path
import pytest
from linda_desktop import config, history, protected_storage as storage

@pytest.fixture
def home(tmp_path,monkeypatch):
    monkeypatch.setenv('LINDA_HOME',str(tmp_path))
    return tmp_path

def result():
    return {'verdict':'human','p_ai':.1,'sentences':[],'private':'confidential result marker'}

def test_history_is_encrypted_including_metadata_and_restart(home):
    item=history.add('confidential document marker',result(),'sensitive',title='Private customer name')
    blob=(home/'history.db').read_bytes()
    assert blob.startswith(storage.MAGIC)
    assert b'Private customer name' not in blob
    with pytest.raises(sqlite3.DatabaseError):
        con=sqlite3.connect(home/'history.db')
        try: con.execute('SELECT * FROM checks').fetchall()
        finally: con.close()
    assert history.get(item)['text']=='confidential document marker'
    assert history.get(item)['result']['private']=='confidential result marker'
    assert not list(home.glob('*.protected-tmp'))

def test_dpapi_purpose_and_integrity_fail_closed(home):
    blob=storage.protect(b'synthetic secret','one')
    assert storage.unprotect(blob,'one')==b'synthetic secret'
    with pytest.raises(ValueError): storage.unprotect(blob,'two')
    corrupted=bytearray(blob);corrupted[-1]^=1
    with pytest.raises(ValueError): storage.unprotect(bytes(corrupted),'one')
    (home/'history.db').write_bytes(bytes(corrupted))
    with pytest.raises(ValueError): history.list_checks()
    assert (home/'history.db').read_bytes()==bytes(corrupted)

def test_legacy_database_migrates_without_plaintext_backup(home):
    con=sqlite3.connect(home/'history.db');con.execute(history.SCHEMA)
    con.execute('INSERT INTO checks (title,ts,words) VALUES (?,?,?)',('Legacy customer',1,2));con.commit();con.close()
    assert history.list_checks()[0]['title']=='Legacy customer'
    assert (home/'history.db').read_bytes().startswith(storage.MAGIC)
    assert len(list(home.iterdir()))==1

def test_failed_write_and_failed_transaction_preserve_history(home,monkeypatch):
    history.add('existing',result(),'sensitive')
    before=(home/'history.db').read_bytes()
    def fail(*args): raise PermissionError('synthetic replacement failure')
    with monkeypatch.context() as m:
        m.setattr(os,'replace',fail)
        with pytest.raises(PermissionError): history.add('new',result(),'sensitive')
    assert (home/'history.db').read_bytes()==before
    with pytest.raises(RuntimeError):
        with history._db() as con:
            con.execute('DELETE FROM checks');raise RuntimeError('synthetic rollback')
    assert history.stats()['n']==1

def test_snapshot_lock_prevents_lost_updates_between_processes(home):
    source=Path(__file__).resolve().parents[1]
    code="from linda_desktop import history; [history.add('synthetic',{'verdict':'human','p_ai':.1,'sentences':[]},'sensitive') for i in range(4)]"
    env=dict(os.environ,PYTHONPATH=str(source),OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    children=[subprocess.Popen([sys.executable,'-c',code],cwd=source,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    for child in children:
        out,err=child.communicate(timeout=20)
        assert child.returncode==0,err.decode(errors='replace')
    assert history.stats()['n']==8
