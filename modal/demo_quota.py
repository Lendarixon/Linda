"""Persistent, transactional demo quota. No texts or raw IP addresses are stored."""
import sqlite3,time,re
from contextlib import closing

MAX_USES=12
DAY_LIMIT=300
LEASE_SECONDS=600

def quota(db_path, operation, visitor, network, request_id=None, now=None):
    now=float(time.time() if now is None else now)
    day=int(now//86400)
    with closing(sqlite3.connect(str(db_path),timeout=10)) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS checks (id TEXT PRIMARY KEY,visitor TEXT,network TEXT,day INTEGER,state TEXT,created REAL)')
        db.execute('CREATE INDEX IF NOT EXISTS visitor_checks ON checks(visitor,state)')
        db.execute('CREATE INDEX IF NOT EXISTS network_checks ON checks(network,day,state)')
        db.execute('BEGIN IMMEDIATE')
        db.execute("DELETE FROM checks WHERE state='pending' AND created<?",(now-LEASE_SECONDS,))
        def count(sql,args):return db.execute(sql,args).fetchone()[0]
        def remaining():
            user=count("SELECT count(*) FROM checks WHERE visitor=? AND state IN ('pending','done')",(visitor,))
            address=count("SELECT count(*) FROM checks WHERE network=? AND day=? AND state IN ('pending','done')",(network,day))
            return max(0,min(MAX_USES-user,MAX_USES-address))
        if operation=='reserve':
            if not request_id:raise ValueError('missing request id')
            if db.execute('SELECT 1 FROM checks WHERE id=?',(request_id,)).fetchone():
                return {'ok':False,'remaining':remaining(),'reason':'duplicate'}
            if not remaining():return {'ok':False,'remaining':0,'reason':'visitor_limit'}
            if count("SELECT count(*) FROM checks WHERE day=? AND state IN ('pending','done')",(day,))>=DAY_LIMIT:
                return {'ok':False,'remaining':remaining(),'reason':'demo_capacity'}
            db.execute("INSERT INTO checks VALUES (?,?,?,?,'pending',?)",(request_id,visitor,network,day,now))
        elif operation in ('finish','refund'):
            if operation=='finish':
                row=db.execute("SELECT state FROM checks WHERE id=? AND visitor=? AND network=?",(request_id,visitor,network)).fetchone()
                if row is None:return {'ok':False,'remaining':remaining(),'reason':'expired'}
                db.execute("UPDATE checks SET state='done' WHERE id=? AND visitor=? AND network=? AND state='pending'",(request_id,visitor,network))
            else:
                db.execute("DELETE FROM checks WHERE id=? AND visitor=? AND network=? AND state='pending'",(request_id,visitor,network))
        elif operation=='remove_owned_test':
            # Maintenance via authenticated Modal RPC only; no HTTP route accepts operations.
            if network!='owner-maintenance' or not re.fullmatch('[0-9a-f]{32}',visitor):raise ValueError('invalid maintenance reference')
            if request_id:
                if not re.fullmatch('[0-9a-f]{32}',request_id):raise ValueError('invalid check reference')
                db.execute('DELETE FROM checks WHERE id=?',(request_id,))
            else:db.execute('DELETE FROM checks WHERE visitor=?',(visitor,))
        elif operation!='status':raise ValueError('unknown quota operation')
        return {'ok':True,'remaining':remaining(),'max_uses':MAX_USES}
