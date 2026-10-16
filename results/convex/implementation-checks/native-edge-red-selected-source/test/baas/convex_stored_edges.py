#!/usr/bin/env python3
"""Actual stored signed64 IDs and join holes, not converter-only proof."""
import os
import unittest
from convex_feasibility import query
from convex_http_writes import mutation
from test_api import request, token

MARKER = os.environ.get('CONVEX_EDGE_PROBE_MARKER', 'tds-native-edge-probe:default:')
WIDE = 9007199254740993
MAXIMUM = 9223372036854775807
BODY = MARKER + 'café\x00😀'


class NativeStoredEdges(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if os.environ.get('CONVEX_EDGE_PROBE_CLEANUP') == '1':
            status, result = mutation('fixtures:resetStoredEdges', {'marker': MARKER})
            if status != 200 or result.get('status') != 'success':
                raise AssertionError('Private exact stored-edge cleanup failed; preserve state, never blindly reseed')

    def test_01_native_stored_fixture_installation(self):
        status, result = mutation('fixtures:installStoredEdges', {'marker': MARKER})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success', 'Private stored-edge fixture primitive missing')
        self.assertEqual(result.get('value'), {'users_added': 1, 'posts_added': 25})

    def test_02_wide_stored_detail_unicode_nul_and_native_identity_like(self):
        status, result = request('GET', '/posts/' + str(WIDE))
        self.assertEqual(status, 200)
        self.assertEqual(result['post']['id'], WIDE)
        self.assertEqual(result['post']['body'], BODY)
        self.assertEqual(result['post']['author'], 'native-wide-user')
        status, result = request('POST', '/posts/' + str(WIDE) + '/like', auth=token(sub=str(WIDE), username='signed-wide-name'))
        self.assertEqual(status, 201)
        self.assertEqual(result, {'liked': True, 'already_liked': False, 'post_id': WIDE})
        self.assertEqual(request('GET', '/posts/' + str(WIDE))[1]['post']['like_count'], 1)

    def test_03_feed_crosses_24_newer_orphan_join_holes(self):
        status, result = request('GET', '/feed')
        self.assertEqual(status, 200, 'Native feed must cross join holes without unsupported repeated pagination')
        self.assertEqual(len(result['posts']), 20)
        self.assertEqual(result['posts'][0]['id'], WIDE)
        self.assertEqual(result['posts'][0]['body'], BODY)
        self.assertTrue(all(post['author'] != 'nonexistent-orphan-user' for post in result['posts']))
        self.assertEqual(request('GET', '/posts/501000'), (404, {'error': 'post not found'}))

    def test_04_maximum_allocation_then_exhaustion_does_not_round_or_advance(self):
        status, result = mutation('fixtures:prepareAllocationBoundary', {'marker': MARKER, 'previous': '0000000000000500000', 'target': '9223372036854775806'})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success')
        status, result = request('POST', '/posts', {'body': MARKER + 'maximum'}, auth=token(sub=str(WIDE), username='signed-wide-name'))
        self.assertEqual(status, 201)
        self.assertEqual(result['post']['id'], MAXIMUM)
        self.assertEqual(result['post']['author'], 'signed-wide-name')
        self.assertEqual(request('GET', '/posts/' + str(MAXIMUM))[1]['post']['id'], MAXIMUM)
        self.assertEqual(request('POST', '/posts', {'body': MARKER + 'must-not-overflow'}, auth=token()), (500, {'error': 'internal server error'}))
        self.assertEqual(query('fixtures:writeProbeState')[1]['value']['sequence'], str(MAXIMUM))

    def test_05_real_collision_after_sequence_patch_rolls_back(self):
        previous, target = str(MAXIMUM), str(WIDE - 1).zfill(19)
        status, result = mutation('fixtures:prepareAllocationBoundary', {'marker': MARKER, 'previous': previous, 'target': target})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success')
        self.assertEqual(request('POST', '/posts', {'body': MARKER + 'must-not-overwrite'}, auth=token()), (500, {'error': 'internal server error'}))
        self.assertEqual(query('fixtures:writeProbeState')[1]['value']['sequence'], target)
        self.assertEqual(request('GET', '/posts/' + str(WIDE))[1]['post']['body'], BODY)


if __name__ == '__main__':
    unittest.main(verbosity=2)
