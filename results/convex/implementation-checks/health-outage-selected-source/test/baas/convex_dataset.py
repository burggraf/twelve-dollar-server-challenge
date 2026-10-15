#!/usr/bin/env python3
"""Full canonical data/query feasibility through real private native APIs."""
import csv
import hashlib
import heapq
import json
import os
from pathlib import Path
import unittest

from convex_feasibility import query

COUNTS = {'users': 50000, 'posts': 500000, 'likes': 2016005}
DIGEST = '738d11ab3164c13177e347f75038d1e80b43c64e754544a42d1c32bd8d7bcf1d'
COLUMNS = {'users': ['id', 'username', 'created_at'], 'posts': ['id', 'user_id', 'body', 'created_at'], 'likes': ['user_id', 'post_id', 'created_at']}


class FullNativeDataset(unittest.TestCase):
    def call(self, path, args=None):
        status, response = query(path, args)
        self.assertEqual(status, 200, 'Native function unavailable: ' + path)
        self.assertEqual(response.get('status'), 'success', 'Native function missing or failed: ' + path)
        return response['value']

    def identity(self, value):
        self.assertIsInstance(value, str)
        self.assertEqual(len(value), 19)
        self.assertTrue(value.isascii() and value.isdecimal())
        self.assertGreater(int(value), 0)
        self.assertLessEqual(int(value), 9223372036854775807)
        return int(value)

    def test_01_full_native_canonical_rows_hash_relations_and_metadata(self):
        digest = hashlib.sha256()
        counts, user_ids, post_ids = {}, set(), set()
        for table, columns in COLUMNS.items():
            cursor, done, previous, count, pages = None, False, None, 0, 0
            while not done:
                result = self.call('native:canonicalPage', {'table': table, 'cursor': cursor})
                pages += 1
                self.assertLess(pages, 10000, 'Native pagination did not terminate')
                self.assertIsInstance(result['isDone'], bool)
                self.assertLessEqual(len(result['page']), 1000)
                for native in result['page']:
                    self.assertEqual(set(native), set(columns) | {'_id', '_creationTime'})
                    self.assertIsInstance(native['_id'], str)
                    self.assertIsInstance(native['_creationTime'], (int, float))
                    row = []
                    for column in columns:
                        value = native[column]
                        if column in ['id', 'user_id', 'post_id']:
                            value = self.identity(value)
                        else:
                            self.assertIsInstance(value, str)
                        row.append(value)
                    if table == 'users':
                        key = row[0]
                        user_ids.add(row[0])
                    elif table == 'posts':
                        key = row[0]
                        self.assertIn(row[1], user_ids)
                        post_ids.add(row[0])
                    else:
                        key = (row[1], row[0])
                        self.assertIn(row[0], user_ids)
                        self.assertIn(row[1], post_ids)
                    if previous is not None:
                        self.assertGreater(key, previous, 'Native logical order/uniqueness differs')
                    previous = key
                    digest.update(('|'.join(map(str, row)) + '\n').encode())
                    count += 1
                cursor, done = result['continueCursor'], result['isDone']
            self.assertEqual(count, COUNTS[table])
            counts[table] = count
        self.assertEqual(digest.hexdigest(), DIGEST)
        result = {'counts': counts, 'content_sha256': digest.hexdigest(), 'scope': 'Actual native paginated API rows; native metadata present; logical IDs/relationships/order/unique likes verified'}
        if os.environ.get('CONVEX_NATIVE_DATASET_MANIFEST'):
            Path(os.environ['CONVEX_NATIVE_DATASET_MANIFEST']).write_text(json.dumps(result, indent=2) + '\n')
        print('Actual native canonical counts/full logical hash verified:', json.dumps(result), flush=True)

    def test_02_native_normalized_feed_detail_and_largest_seed_count(self):
        # Demand a real function before doing any local oracle preparation.
        actual = self.call('native:feed')
        seed = Path(os.environ.get('CONVEX_SEED_DIR', '/state/convex/seed'))
        def rows(table):
            with (seed / (table + '.tsv')).open(newline='', encoding='utf-8') as stream:
                yield from csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE)
        users = {row[0]: row[1] for row in rows('users')}
        newest = heapq.nlargest(20, rows('posts'), key=lambda row: (row[3], int(row[0])))
        like_counts = {}
        for user, post, created in rows('likes'):
            like_counts[post] = like_counts.get(post, 0) + 1
        expected = [{'id': row[0], 'body': row[2], 'created_at': row[3], 'author': users[row[1]], 'like_count': like_counts.get(row[0], 0)} for row in newest]
        self.assertEqual(actual, expected)
        for post in expected:
            self.assertEqual(self.call('native:detail', {'id': post['id'].zfill(19)}), post)
        most_liked = max(like_counts, key=like_counts.get)
        popular = self.call('native:detail', {'id': most_liked.zfill(19)})
        self.assertEqual(popular['like_count'], like_counts[most_liked])
        self.assertEqual(like_counts[most_liked], 583)
        print('Native feed/detail exact normalized counts verified; largest seeded post:', most_liked, 'likes:', popular['like_count'], flush=True)

    def test_03_native_read_functions_are_private(self):
        for path, args in [('native:canonicalPage', {'table': 'users', 'cursor': None}), ('native:feed', {}), ('native:detail', {'id': '0000000000000000001'})]:
            with self.subTest(function=path):
                status, result = query(path, args, authorized=False)
                self.assertTrue(status >= 400 or result.get('status') == 'error', 'Internal data query exposed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
