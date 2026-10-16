#!/usr/bin/env python3
"""Unchanged specification error text on the actual native site."""
import unittest
from convex_http_auth import raw_request


class NativeErrorContract(unittest.TestCase):
    def test_malformed_json_uses_original_contract_message(self):
        self.assertEqual(raw_request(b'{'), (400, {'error': 'malformed JSON body'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
