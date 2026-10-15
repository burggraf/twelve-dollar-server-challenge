"""Exercise the offline mapping on a real native-bootstrapped schema copy.

POCKETBASE_NATIVE_FIXTURE must name the private empty schema snapshot created
from the owned real PocketBase runtime, not hand-written replacement tables.
"""
import csv
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
import import_pocketbase as importer


class NativeImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture = Path(os.environ['POCKETBASE_NATIVE_FIXTURE'])
        self.assertTrue(fixture.is_file(), 'Real native-bootstrapped schema evidence required')
        database = self.root / 'data.db'
        shutil.copyfile(fixture, database)
        self.conn = sqlite3.connect(database)
        self.addCleanup(self.conn.close)
        importer.require_native_schema(self.conn)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM feed_posts').fetchone()[0], 0)
        self.before = importer.platform_fingerprint(self.conn)
        self.rows = {
            'users': [['1', 'first', '2025-01-01T00:00:00.000Z'],
                      ['9223372036854775807', 'Ω\x00🙂', '2025-01-01T00:00:00.000Z']],
            'posts': [['2', '1', 'body', '2025-01-01T00:00:00.000Z'],
                      ['10', '9223372036854775807', '\u0085Ω\x00🙂', '2025-01-01T00:00:00.000Z']],
            'likes': [['9223372036854775807', '10', '2025-01-01T00:00:00.000Z']],
        }

    def import_fixture(self):
        digest = hashlib.sha256()
        for table, rows in self.rows.items():
            with (self.root / (table + '.tsv')).open('w', newline='') as stream:
                csv.writer(stream, delimiter='\t', quoting=csv.QUOTE_NONE, lineterminator='\n').writerows(rows)
            for row in rows:
                digest.update(('|'.join(row) + '\n').encode())
        with patch.object(importer, 'EXPECTED_COUNTS', {table: len(rows) for table, rows in self.rows.items()}), \
             patch.object(importer, 'EXPECTED_HASH', digest.hexdigest()):
            return importer.import_data(self.conn, self.root)

    def test_lossless_native_mapping_and_platform_preservation(self):
        result = self.import_fixture()
        self.assertEqual(self.conn.execute('SELECT body FROM feed_posts WHERE id="10"').fetchone()[0], '\u0085Ω\x00🙂')
        self.assertEqual(self.conn.execute('SELECT user_id FROM feed_posts WHERE id="10"').fetchone()[0], '9223372036854775807')
        self.assertEqual(self.conn.execute('SELECT id FROM feed_posts ORDER BY CAST(id AS INTEGER) DESC').fetchall(), [('10',), ('2',)])
        self.assertEqual(result['next_post_id'], 11)
        self.assertEqual(self.conn.execute('SELECT last_id FROM feed_sequences').fetchone()[0], '10')
        self.assertEqual(result['platform_rows_before_sha256'], self.before)
        self.assertEqual(result['platform_rows_after_sha256'], self.before)
        self.assertEqual(len(self.conn.execute('SELECT id FROM feed_likes').fetchone()[0]), 15)

    def test_missing_native_relation_rolls_back_entire_application_import(self):
        self.rows['likes'][0][1] = '999'
        with self.assertRaisesRegex(ValueError, 'Logical native relationship'):
            self.import_fixture()
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM feed_users').fetchone()[0], 0)
        self.assertEqual(self.conn.execute('SELECT last_id FROM feed_sequences').fetchone()[0], '0')
        self.assertEqual(importer.platform_fingerprint(self.conn), self.before)

    def test_wrong_canonical_hash_rolls_back_without_touching_native_auth(self):
        for table, rows in self.rows.items():
            with (self.root / (table + '.tsv')).open('w', newline='') as stream:
                csv.writer(stream, delimiter='\t', quoting=csv.QUOTE_NONE).writerows(rows)
        with patch.object(importer, 'EXPECTED_COUNTS', {table: len(rows) for table, rows in self.rows.items()}):
            with self.assertRaisesRegex(ValueError, 'Canonical logical content hash mismatch'):
                importer.import_data(self.conn, self.root)
        self.assertEqual(self.conn.execute('SELECT COUNT(*) FROM feed_posts').fetchone()[0], 0)
        self.assertEqual(importer.platform_fingerprint(self.conn), self.before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
