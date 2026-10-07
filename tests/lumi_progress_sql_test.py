"""Execute the production progress queries against isolated history fixtures."""
from pathlib import Path
import re
import sqlite3

root = Path(__file__).resolve().parents[1]
sql = dict(re.findall(r'(\w+) :: #string SQL\n(.*?)\nSQL',
                      (root / 'src/cells/lumi_progress.zi').read_text(), re.S))
schema = dict(re.findall(r'(\w+) :: #string SQL\n(.*?)\nSQL',
                         (root / 'src/storage/schema_sql.zi').read_text(), re.S))
with sqlite3.connect(':memory:') as db:
    db.executescript(schema['SchemaSessions'])
    for index in range(60):
        db.execute("INSERT INTO sessions(id,user_id,started_at,local_date,activity,source,imported_at,rounds_hash) "
                   "VALUES(?,?,?,?,?,'test',1,?)",
                   (str(index), 'owner', index, 20261007, index % 2, index))
        db.execute('INSERT INTO session_rounds VALUES(?,0,?)', (str(index), 120 if index % 2 else 75))
    db.execute("INSERT INTO sessions VALUES('foreign','other',100,20261007,0,0,'test',1,100,0,0,0,0,'','',0,1)")
    db.execute("INSERT INTO sessions VALUES('deleted','owner',101,20261007,0,0,'test',1,101,0,0,0,0,'','',1,1)")
    db.execute("INSERT INTO session_rounds VALUES('foreign',0,900)")
    db.execute("INSERT INTO session_rounds VALUES('deleted',0,999)")
    query = sql['LumiProgressSessionsSql']
    assert db.execute(query, ('owner', 20261001, 20261007, 0)).fetchall() == [(20261007, 60)]
    assert db.execute(query, ('owner', 20261001, 20261007, 1)).fetchall() == [(20261007, 3600)]
    assert db.execute(query, ('owner', 20261001, 20261007, 2)).fetchall() == [(20261007, 75)]
    assert db.execute(query, ('owner', 20261008, 20261010, 0)).fetchall() == []
    # Older meditation logs remain visible without double-counting sessions;
    # a log attached to a deleted session must stay deleted.
    db.execute("INSERT INTO meditation_logs VALUES('known','owner','1',150,0,1)")
    db.execute("INSERT INTO meditation_logs VALUES('hidden','owner','deleted',800,0,1)")
    db.execute("INSERT INTO meditation_logs VALUES('legacy','owner','missing',90,strftime('%s','2026-10-07 12:00:00'),1)")
    db.execute("INSERT INTO meditation_logs VALUES('other-log','other','other-missing',500,strftime('%s','2026-10-07 12:00:00'),1)")
    assert db.execute(query, ('owner', 20261001, 20261007, 0)).fetchall() == [(20261007, 61)]
    assert db.execute(query, ('owner', 20261001, 20261007, 1)).fetchall() == [(20261007, 3720)]
    linked = sql['LumiProgressLinkedSql']
    assert db.execute(linked, ('owner', 20261007, 1, 1)).fetchone() == (30,)
    assert db.execute(linked, ('owner', 20261007, 1, 2)).fetchone() == (30,)
    assert db.execute(linked, ('owner', 20261007, 0, 15)).fetchone() == (0,)
print('Progress SQL: more than 48 sessions, deleted rows, account boundaries, units and linked activity masks passed')
