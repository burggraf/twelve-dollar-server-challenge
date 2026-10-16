#!/usr/bin/env python3
"""Read-only compatibility HTTP gate against the actual native serving stack.

Run only on the designated VPS. Private native reads provide a serialization
oracle; the separate canonical verifier establishes stored contents independently.
"""
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

from convex_feasibility import metrics, query

BASE = os.environ.get('CONVEX_SITE_URL', 'http://backend:3211').rstrip('/')


class NativeHttpReads(unittest.TestCase):
    def get(self, path, status):
        try:
            response = urlopen(BASE + path, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            self.assertEqual(response.status, status, 'Wrong compatibility HTTP status: ' + path)
            self.assertTrue(response.headers.get('Content-Type', '').lower().startswith('application/json'), 'Compatibility HTTP response is not JSON')
        text = raw.decode('utf-8')
        try:
            value = json.loads(text)
        except ValueError:
            self.fail('Compatibility response is not valid JSON')
        # Optional JSON escapes are allowed; insignificant interior whitespace is not.
        quoted = escaped = False
        for character in text.rstrip('\n'):
            if quoted:
                if escaped:
                    escaped = False
                elif character == '\\':
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            else:
                self.assertNotIn(character, ' \t\r\n', 'Noncompact compatibility JSON')
        return value

    def native(self, path, args=None):
        status, result = query(path, args)
        self.assertEqual(status, 200, 'Native oracle unavailable')
        self.assertEqual(result.get('status'), 'success', 'Native oracle query failed')
        return result['value']

    def post(self, value):
        self.assertEqual(list(value), ['id', 'body', 'created_at', 'author', 'like_count'])
        for field in ['id', 'like_count']:
            self.assertIs(type(value[field]), int, 'Compatibility numeric field must be an exact JSON integer')
        self.assertGreater(value['id'], 0)
        self.assertGreaterEqual(value['like_count'], 0)
        for field in ['body', 'created_at', 'author']:
            self.assertIsInstance(value[field], str)

    def test_01_feed_exact_native_projection_and_key_order(self):
        value = self.get('/feed', 200)
        self.assertEqual(list(value), ['posts'])
        self.assertEqual(len(value['posts']), 20)
        expected = self.native('native:feed')
        expected = [{**post, 'id': int(post['id']), 'like_count': int(post['like_count'])} for post in expected]
        self.assertEqual(value['posts'], expected)
        for post in value['posts']:
            self.post(post)

    def test_02_detail_leading_zero_identity_and_largest_seed_count(self):
        for text in ['405018', '0000000000000405018']:
            with self.subTest(identity=text):
                value = self.get('/posts/' + text, 200)
                self.assertEqual(list(value), ['post'])
                self.post(value['post'])
                expected = self.native('native:detail', {'id': '405018'.zfill(19)})
                self.assertEqual(value['post'], {**expected, 'id': 405018, 'like_count': 583})

    def test_03_invalid_ids_fail_without_unsafe_numeric_coercion(self):
        for text in ['0', '-1', 'abc', '1.5', '9223372036854775808']:
            with self.subTest(identity=text):
                self.assertEqual(self.get('/posts/' + text, 400), {'error': 'invalid post id'})

    def test_04_absent_positive_signed64_ids_are_not_invalid(self):
        for text in ['500001', '9007199254740993', '9223372036854775807']:
            with self.subTest(identity=text):
                self.assertEqual(self.get('/posts/' + text, 404), {'error': 'post not found'})

    def test_05_unknown_paths_have_exact_json_error(self):
        for path in ['/does-not-exist', '/posts/1/extra']:
            with self.subTest(path=path):
                self.assertEqual(self.get(path, 404), {'error': 'not found'})

    def test_06_each_http_feed_reexecutes_its_native_query(self):
        before = metrics()
        for _ in range(5):
            self.get('/feed', 200)
        after = metrics()
        self.assertGreaterEqual(after['cache_plan_go_total'] - before['cache_plan_go_total'], 5)
        self.assertEqual(after['cache_plan_ready_total'], before['cache_plan_ready_total'])
        self.assertEqual(after['cache_plan_wait_total'], before['cache_plan_wait_total'])
        self.assertEqual(after['cache_size_bytes'], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
