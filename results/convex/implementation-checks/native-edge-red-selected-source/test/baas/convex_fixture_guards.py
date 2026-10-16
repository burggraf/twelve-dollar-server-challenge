#!/usr/bin/env python3
"""Non-destructive ownership controls for untimed admin-only probe cleanup."""
import os
import unittest
from convex_feasibility import query
from convex_http_writes import mutation
from test_api import request, token

MARKER = os.environ.get('CONVEX_WRITE_GUARD_MARKER', 'tds-native-write-probe:guard-default:')


class NativeFixtureGuards(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if os.environ.get('CONVEX_WRITE_GUARD_CLEANUP') == '1':
            status, result = mutation('fixtures:resetWriteProbe', {'marker': MARKER})
            if status != 200 or result.get('status') != 'success':
                raise AssertionError('Guard probe exact-owned cleanup failed; preserve state')

    def state(self):
        status, result = query('fixtures:writeProbeState')
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success')
        return result['value']

    def test_01_internal_probe_state_is_private_with_positive_control(self):
        self.assertEqual(self.state(), {'sequence': '0000000000000500000', 'extra_posts': 0})
        status, result = query('fixtures:writeProbeState', authorized=False)
        self.assertTrue(status >= 400 or result.get('status') == 'error')
        self.assertEqual(self.state(), {'sequence': '0000000000000500000', 'extra_posts': 0})

    def test_02_invalid_namespaces_cannot_reset_even_empty_state(self):
        before = self.state()
        for marker in ['', 'tds-native-write-probe:', 'unrelated:', 'tds-native-write-probe:has space:', 'tds-native-write-probe:' + 'a' * 65 + ':']:
            with self.subTest(length=len(marker)):
                status, result = mutation('fixtures:resetWriteProbe', {'marker': marker})
                self.assertTrue(status >= 400 or result.get('status') == 'error')
                self.assertEqual(self.state(), before)
        status, result = mutation('fixtures:resetWriteProbe', {'marker': MARKER})
        self.assertEqual((status, result.get('status'), result.get('value')), (200, 'success', {'deleted_posts': 0, 'deleted_likes': 0}))

    def test_03_valid_but_wrong_namespace_refuses_other_owned_rows(self):
        status, result = request('POST', '/posts', {'body': MARKER + 'ownership-guard'}, auth=token())
        self.assertEqual(status, 201)
        post_id = result['post']['id']
        before = self.state()
        self.assertEqual(before['extra_posts'], 1)
        status, result = mutation('fixtures:resetWriteProbe', {'marker': 'tds-native-write-probe:other-owned-attempt:'})
        self.assertTrue(status >= 400 or result.get('status') == 'error', 'Cleanup accepted another valid namespace and could destroy its posts')
        self.assertEqual(self.state(), before)
        status, result = request('GET', '/posts/' + str(post_id))
        self.assertEqual(status, 200)
        self.assertEqual(result['post']['body'], MARKER + 'ownership-guard')


if __name__ == '__main__':
    unittest.main(verbosity=2)
