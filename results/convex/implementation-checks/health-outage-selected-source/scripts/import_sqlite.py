#!/usr/bin/env python3
"""Offline application-table import. Never replaces platform metadata or opens a live server DB.

The lifecycle wrapper stops the platform first. Input is the unchanged canonical TSV export.
"""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3

EXPECTED_HASH = '738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d'
EXPECTED_COUNTS = {'users': 50_000, 'posts': 500_000, 'likes': 2_016_005}


def verify(conn):
    digest = hashlib.sha256()
    counts = {}
    for table, order in [('users', 'id'), ('posts', 'id'), ('likes', 'post_id,user_id')]:
        counts[table] = conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
        if counts[table] != EXPECTED_COUNTS[table]:
            raise ValueError(f'{table}: {counts[table]} rows, expected {EXPECTED_COUNTS[table]}')
        if conn.execute(f'PRAGMA foreign_key_check({table})').fetchone():
            raise ValueError(f'{table}: foreign key violation')
        for row in conn.execute(f'SELECT * FROM {table} ORDER BY {order}'):
            digest.update(('|'.join(map(str, row)) + '\n').encode())
    if digest.hexdigest() != EXPECTED_HASH:
        raise ValueError(f'Content hash mismatch: {digest.hexdigest()}')
    return {'counts': counts, 'content_sha256': digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('tsv', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error('Platform must bootstrap its database/migrations before import')
    with sqlite3.connect(args.database) as conn:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('BEGIN IMMEDIATE')
        for table in ['likes', 'posts', 'users']:
            conn.execute(f'DELETE FROM {table}')
        for table, columns in [('users', 3), ('posts', 4), ('likes', 3)]:
            with (args.tsv / (table + '.tsv')).open(newline='') as stream:
                rows = csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE)
                while batch := list(itertools.islice(rows, 5000)):
                    conn.executemany(f'INSERT INTO {table} VALUES({",".join("?" * columns)})', batch)
        manifest = verify(conn)
        conn.commit()
        conn.execute('ANALYZE')
        conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest))


if __name__ == '__main__':
    main()
