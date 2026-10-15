#!/usr/bin/env python3
"""Offline app-only import into an already bootstrapped native PocketBase DB.

The owned lifecycle must stop PocketBase before calling this. Never replaces
native collections, Auth accounts, settings, migrations or the auxiliary DB.
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3

from import_sqlite import EXPECTED_COUNTS, EXPECTED_HASH

SEQUENCE_ID = 'feedpostcounter'
APP_COLUMNS = {
    'feed_users': {'id', 'username', 'created_at'},
    'feed_posts': {'id', 'user_id', 'body', 'created_at'},
    'feed_likes': {'id', 'user_id', 'post_id', 'created_at'},
    'feed_sequences': {'id', 'last_id'},
}


def require_native_schema(conn):
    for table, wanted in APP_COLUMNS.items():
        row = conn.execute('SELECT type FROM _collections WHERE name=?', (table,)).fetchone()
        if row != ('base',):
            raise ValueError('Missing native application base collection: ' + table)
        columns = {row[1]: row for row in conn.execute(f'PRAGMA table_info({table})')}
        if set(columns) != wanted or columns['id'][2] != 'TEXT' or columns['id'][5] != 1:
            raise ValueError('Native collection storage mapping differs: ' + table)
    if conn.execute('SELECT COUNT(*) FROM feed_sequences WHERE id=?', (SEQUENCE_ID,)).fetchone()[0] != 1:
        raise ValueError('Native migration must create persistent post allocation metadata')


def platform_fingerprint(conn):
    """Hash, never export, private native platform rows; planner stats excluded."""
    digest = hashlib.sha256()
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
              if row[0] not in APP_COLUMNS and not row[0].startswith('sqlite_')]
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        rows = []
        for row in conn.execute('SELECT * FROM ' + quoted):
            values = [{'blob_hex': value.hex()} if isinstance(value, bytes) else value for value in row]
            rows.append(json.dumps(values, ensure_ascii=True, separators=(',', ':')).encode())
        digest.update(table.encode() + b'\0')
        for raw in sorted(rows):
            digest.update(raw + b'\0')
    return digest.hexdigest()


def verify(conn):
    digest = hashlib.sha256()
    counts = {}
    queries = {
        'users': 'SELECT CAST(id AS INTEGER),username,created_at FROM feed_users ORDER BY CAST(id AS INTEGER)',
        'posts': 'SELECT CAST(id AS INTEGER),CAST(user_id AS INTEGER),body,created_at FROM feed_posts ORDER BY CAST(id AS INTEGER)',
        'likes': 'SELECT CAST(user_id AS INTEGER),CAST(post_id AS INTEGER),created_at FROM feed_likes ORDER BY CAST(post_id AS INTEGER),CAST(user_id AS INTEGER)',
    }
    for table, fields in [('feed_users', ['id']), ('feed_posts', ['id', 'user_id']), ('feed_likes', ['user_id', 'post_id'])]:
        for field in fields:
            bad = conn.execute(f'SELECT 1 FROM {table} WHERE {field} != CAST(CAST({field} AS INTEGER) AS TEXT) OR CAST({field} AS INTEGER)<=0 LIMIT 1').fetchone()
            if bad:
                raise ValueError('Noncanonical native decimal identity: ' + table + '.' + field)
    for query in [
        'SELECT 1 FROM feed_posts p LEFT JOIN feed_users u ON u.id=p.user_id WHERE u.id IS NULL LIMIT 1',
        'SELECT 1 FROM feed_likes l LEFT JOIN feed_users u ON u.id=l.user_id LEFT JOIN feed_posts p ON p.id=l.post_id WHERE u.id IS NULL OR p.id IS NULL LIMIT 1',
        'SELECT 1 FROM feed_likes GROUP BY user_id,post_id HAVING COUNT(*)>1 LIMIT 1',
    ]:
        if conn.execute(query).fetchone():
            raise ValueError('Logical native relationship/unique-like integrity failed')
    for table, query in queries.items():
        counts[table] = conn.execute('SELECT COUNT(*) FROM feed_' + table).fetchone()[0]
        if counts[table] != EXPECTED_COUNTS[table]:
            raise ValueError(f'{table}: {counts[table]} rows, expected {EXPECTED_COUNTS[table]}')
        for row in conn.execute(query):
            digest.update(('|'.join(map(str, row)) + '\n').encode())
    if digest.hexdigest() != EXPECTED_HASH:
        raise ValueError('Canonical logical content hash mismatch: ' + digest.hexdigest())
    return {'counts': counts, 'content_sha256': digest.hexdigest()}


def import_data(conn, tsv):
    require_native_schema(conn)
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('BEGIN IMMEDIATE')
    try:
        before = platform_fingerprint(conn)
        for table in ['feed_likes', 'feed_posts', 'feed_users']:
            conn.execute('DELETE FROM ' + table)
        for table, columns in [('users', ['id', 'username', 'created_at']),
                               ('posts', ['id', 'user_id', 'body', 'created_at']),
                               ('likes', ['user_id', 'post_id', 'created_at'])]:
            with (tsv / (table + '.tsv')).open(newline='', encoding='utf-8') as stream:
                rows = csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE)
                if table == 'likes':
                    # Deterministic native extra IDs only; the original logical
                    # compound (user_id,post_id) key and hash remain unchanged.
                    rows = ([f'{index:015x}', *row] for index, row in enumerate(rows, 1))
                    columns = ['id', *columns]
                statement = f'INSERT INTO feed_{table} ({",".join(columns)}) VALUES ({",".join("?" for _ in columns)})'
                while batch := list(itertools.islice(rows, 5000)):
                    conn.executemany(statement, batch)
        maximum = conn.execute('SELECT MAX(CAST(id AS INTEGER)) FROM feed_posts').fetchone()[0]
        changed = conn.execute('UPDATE feed_sequences SET last_id=? WHERE id=?', (str(maximum), SEQUENCE_ID)).rowcount
        if changed != 1:
            raise ValueError('Native post allocation metadata missing')
        manifest = verify(conn)
        after = platform_fingerprint(conn)
        if before != after:
            raise ValueError('Native platform metadata changed during application-only import')
        manifest.update({'platform_rows_before_sha256': before, 'platform_rows_after_sha256': after,
                         'next_post_id': maximum + 1,
                         'native_auth_accounts': {table: conn.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
                                                  for table in ['users', '_superusers']},
                         'storage_mapping': 'Native base collections; decimal Text user/post IDs; extra deterministic imported like record IDs; logical compound likes key; persistent transactional post sequence',
                         'scope': 'Offline application-only import; native platform/Auth metadata retained; native relation validation is not a physical SQLite FK declaration'})
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    conn.execute('ANALYZE')
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('tsv', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('PocketBase must bootstrap its native collection migrations first')
    with sqlite3.connect(args.database, timeout=30) as conn:
        manifest = import_data(conn, args.tsv)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
