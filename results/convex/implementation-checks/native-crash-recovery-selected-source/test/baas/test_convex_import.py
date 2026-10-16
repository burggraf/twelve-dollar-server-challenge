#!/usr/bin/env python3
"""Lossless native JSONLines preparation; no access to Convex's SQL storage."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))


class JsonLinesImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tsv, self.output = self.root / 'tsv', self.root / 'native'
        self.tsv.mkdir()
        self.rows = {
            'users': [['1', 'user_one', '2026-01-01T00:00:00.000Z'], ['9007199254740993', 'user_two', '2026-01-01T00:00:00.000Z']],
            'posts': [['9007199254740993', '1', 'NUL\x00 café 😀 \\"', '2026-01-01T00:00:00.000Z'], ['9223372036854775807', '9007199254740993', 'second', '2026-01-01T00:00:00.000Z']],
            'likes': [['9007199254740993', '9007199254740993', '2026-01-01T00:00:00.000Z'], ['1', '9007199254740993', '2026-01-01T00:00:00.000Z']],
        }
        self.save()
        path = ROOT / 'scripts/import_convex.py'
        self.assertTrue(path.is_file(), 'Supported Convex JSONLines preparation is not implemented')
        spec = importlib.util.spec_from_file_location('import_convex', path)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def save(self):
        for table, rows in self.rows.items():
            (self.tsv / (table + '.tsv')).write_text(''.join('\t'.join(row) + '\n' for row in rows), encoding='utf-8')

    def expected(self):
        digest = hashlib.sha256()
        for table in ['users', 'posts', 'likes']:
            key = (lambda row: (int(row[1]), int(row[0]))) if table == 'likes' else (lambda row: int(row[0]))
            for row in sorted(self.rows[table], key=key):
                digest.update(('|'.join(row) + '\n').encode())
        return {table: len(rows) for table, rows in self.rows.items()}, digest.hexdigest()

    def convert(self):
        counts, digest = self.expected()
        return self.module.export_jsonl(self.tsv, self.output, expected_counts=counts, expected_hash=digest)

    def test_lossless_wide_ids_text_native_files_and_hash(self):
        result = self.convert()
        self.assertEqual(result['content_sha256'], self.expected()[1])
        self.assertEqual(result['counts'], self.expected()[0])
        posts = [json.loads(line) for line in (self.output / 'posts.jsonl').read_text().splitlines()]
        self.assertEqual(posts[0], {'id': '0009007199254740993', 'user_id': '0000000000000000001', 'body': self.rows['posts'][0][2], 'created_at': self.rows['posts'][0][3]})
        self.assertEqual(posts[1]['id'], '9223372036854775807')
        self.assertLess(posts[0]['id'], posts[1]['id'])
        sequences = [json.loads(line) for line in (self.output / 'feed_sequences.jsonl').read_text().splitlines()]
        self.assertEqual(sequences, [{'name': 'posts', 'last_id': '9223372036854775807'}])
        self.assertEqual({p.name for p in self.output.iterdir()}, {'users.jsonl', 'posts.jsonl', 'likes.jsonl', 'feed_sequences.jsonl'})
        self.assertNotIn(bytes([0]), (self.output / 'posts.jsonl').read_bytes())

    def test_noncanonical_and_out_of_range_ids_fail_without_output(self):
        for value in ['0', '01', '+1', '-1', '9223372036854775808']:
            with self.subTest(value=value):
                self.rows['users'][0][0] = value
                self.save()
                with self.assertRaises(ValueError):
                    self.convert()
                self.assertFalse(self.output.exists())

    def test_missing_relationship_and_duplicate_like_fail_without_output(self):
        self.rows['posts'][0][1] = '2'
        self.save()
        with self.assertRaises(ValueError):
            self.convert()
        self.assertFalse(self.output.exists())
        self.rows['posts'][0][1] = '1'
        self.rows['likes'].append(self.rows['likes'][0].copy())
        self.save()
        with self.assertRaises(ValueError):
            self.convert()
        self.assertFalse(self.output.exists())

    def test_hash_mismatch_and_existing_destination_never_replace_data(self):
        counts, _ = self.expected()
        with self.assertRaises(ValueError):
            self.module.export_jsonl(self.tsv, self.output, expected_counts=counts, expected_hash='0' * 64)
        self.assertFalse(self.output.exists())
        self.output.mkdir()
        marker = self.output / 'keep'
        marker.write_text('retain')
        with self.assertRaises(FileExistsError):
            self.convert()
        self.assertEqual(marker.read_text(), 'retain')


if __name__ == '__main__':
    unittest.main(verbosity=2)
