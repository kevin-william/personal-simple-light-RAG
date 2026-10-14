from pathlib import Path
from hashlib import sha256
import sqlite3


class Catalog:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS versions (
              id TEXT PRIMARY KEY, hash TEXT NOT NULL, fingerprint TEXT NOT NULL,
              state TEXT NOT NULL CHECK(state IN ('pending','active','failed')),
              expected INTEGER NOT NULL DEFAULT 0, error TEXT);
            CREATE TABLE IF NOT EXISTS sources (
              id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE,
              version TEXT NOT NULL REFERENCES versions(id));
            CREATE TABLE IF NOT EXISTS meta (id INTEGER PRIMARY KEY, generation INTEGER NOT NULL);
            INSERT OR IGNORE INTO meta VALUES (1,0);
            PRAGMA user_version=1;
        ''')

    @staticmethod
    def source_id(path):
        # Windows canonical path comparisons are case-insensitive.
        import os
        return sha256(os.path.normcase(str(Path(path).resolve())).encode()).hexdigest()

    @property
    def generation(self):
        return self.db.execute('SELECT generation FROM meta WHERE id=1').fetchone()[0]

    def source(self, path):
        row = self.db.execute('SELECT * FROM sources WHERE id=?',(self.source_id(path),)).fetchone()
        return dict(row) if row else None

    def version(self, identifier):
        row = self.db.execute('SELECT * FROM versions WHERE id=?',(identifier,)).fetchone()
        return dict(row) if row else None

    def stage(self, version, content_hash, fingerprint, expected):
        if self.version(version) and self.version(version)['state'] == 'active':
            raise ValueError('Não alterar versão ativa durante preparação.')
        with self.db:
            self.db.execute('INSERT INTO versions VALUES (?,?,?,\'pending\',?,NULL) '
                            'ON CONFLICT(id) DO UPDATE SET state=\'pending\',expected=excluded.expected,error=NULL',
                            (version, content_hash, fingerprint, expected))

    def fail(self, version, error):
        with self.db:
            self.db.execute("UPDATE versions SET state='failed',error=? WHERE id=? AND state!='active'",(str(error),version))

    def activate(self, version, path):
        row = self.version(version)
        if not row or row['state'] not in {'pending','active'} or row['expected'] <= 0:
            raise ValueError('Versão não pode ser ativada.')
        identifier = self.source_id(path)
        with self.db:
            self.db.execute("UPDATE versions SET state='active',error=NULL WHERE id=?",(version,))
            self.db.execute('INSERT INTO sources VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,path=excluded.path',
                            (identifier,str(Path(path).resolve()),version))
            self.db.execute('UPDATE meta SET generation=generation+1 WHERE id=1')
        return identifier

    def list_sources(self):
        return [dict(row) for row in self.db.execute('SELECT s.*,v.expected AS chunks FROM sources s JOIN versions v ON s.version=v.id ORDER BY s.path')]

    def active_versions(self):
        return {r[0] for r in self.db.execute("SELECT DISTINCT s.version FROM sources s JOIN versions v ON s.version=v.id WHERE v.state='active'")}

    def all_versions(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM versions')]

    def forget_version(self, version):
        with self.db:
            self.db.execute('DELETE FROM versions WHERE id=? AND id NOT IN (SELECT version FROM sources)',(version,))

    def remove_source(self, identifier):
        with self.db:
            count = self.db.execute('DELETE FROM sources WHERE id=?',(identifier,)).rowcount
            if count:
                self.db.execute('UPDATE meta SET generation=generation+1 WHERE id=1')
        return bool(count)

    def clear(self):
        # Remove visibility before vector cleanup. Orphan versions drive recovery.
        with self.db:
            self.db.execute('DELETE FROM sources')
            self.db.execute('UPDATE meta SET generation=generation+1 WHERE id=1')

    def close(self):
        self.db.close()
