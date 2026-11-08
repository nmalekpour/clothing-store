"""Test helper: an in-memory SQLite stand-in for the RDS MySQL connection.

Loads backend/db/schema.sql (minus MySQL-only statements) and adapts pymysql's %s placeholders,
so the Lambda tests exercise their real SQL without a network database.
"""
import re
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / 'db' / 'schema.sql'


class Cursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._cursor.close()

    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?').replace(' FOR UPDATE', '').replace('INSERT IGNORE', 'INSERT OR IGNORE')
        return self._cursor.execute(sql, params)

    def executemany(self, sql, rows):
        return self._cursor.executemany(sql.replace('%s', '?'), rows)

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid


class Connection:
    open = True

    def __init__(self, schema=SCHEMA):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        script = Path(schema).read_text()
        script = re.sub(r'^(CREATE DATABASE|USE)\b.*$', '', script, flags=re.M | re.I)
        script = re.sub(r'\b(?:bigint|int) auto_increment primary key', 'INTEGER PRIMARY KEY AUTOINCREMENT', script, flags=re.I)
        self.db.executescript(script)

    def cursor(self):
        return Cursor(self.db.cursor())

    def begin(self):
        self.db.execute('BEGIN')

    def commit(self):
        self.db.execute('COMMIT')

    def rollback(self):
        if self.db.in_transaction:
            self.db.execute('ROLLBACK')

    def close(self):
        self.db.close()

    def query(self, sql, params=()):
        return self.db.execute(sql, params).fetchall()
