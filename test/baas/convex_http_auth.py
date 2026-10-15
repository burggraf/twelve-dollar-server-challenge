#!/usr/bin/env python3
"""Actual native site auth-gate regressions; rejected requests must not write data."""
import unittest
from test_api import request


class NativeHttpAuthGate(unittest.TestCase):
    def test_missing_bearer_precedes_post_body_and_like_id_validation(self):
        for path in ['/posts', '/posts/1/like', '/posts/not-an-id/like']:
            with self.subTest(path=path):
                self.assertEqual(request('POST', path, {'body': 'must never be stored'}),
                                 (401, {'error': 'missing bearer token'}))

    def test_malformed_bearer_precedes_post_body_and_like_id_validation(self):
        for path in ['/posts', '/posts/1/like', '/posts/not-an-id/like']:
            with self.subTest(path=path):
                self.assertEqual(request('POST', path, {'body': 'must never be stored'}, auth='not-a-jwt'),
                                 (401, {'error': 'invalid or expired token'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
