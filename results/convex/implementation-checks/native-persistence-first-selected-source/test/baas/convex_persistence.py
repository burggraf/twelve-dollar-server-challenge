#!/usr/bin/env python3
"""Actual acknowledged HTTP post/like/allocation before and after a clean stack restart.

The external owned controller performs the Docker stop/start, never this test or
an application HTTP route. No credentials/JWTs are written to this manifest.
"""
import json
import os
from pathlib import Path
import unittest
from convex_feasibility import query
from convex_http_writes import mutation
from test_api import request, token

BASELINE = '0000000000000500000'
MARKER = os.environ.get('CONVEX_PERSISTENCE_MARKER', 'tds-native-write-probe:persistence-20261015:')
MANIFEST = Path(os.environ.get('CONVEX_PERSISTENCE_MANIFEST', '/state/convex/acknowledged-persistence.json'))
PHASE = os.environ.get('CONVEX_PERSISTENCE_PHASE')


class NativeAcknowledgedPersistence(unittest.TestCase):
    def test_real_acknowledged_post_exactly_once_like_and_sequence(self):
        self.assertIn(PHASE, ['before', 'after'])
        if PHASE == 'before':
            self.assertFalse(MANIFEST.exists(), 'Never overwrite an acknowledged-write attempt')
            _, state = query('fixtures:writeProbeState')
            self.assertEqual(state.get('status'), 'success')
            self.assertEqual(state['value'], {'sequence': BASELINE, 'extra_posts': 0})
            status, response = request('POST', '/posts', {'body': MARKER + 'acknowledged'}, token())
            self.assertEqual(status, 201)
            post = response['post']
            self.assertEqual(post['id'], 500001)
            self.assertEqual(post['body'], MARKER + 'acknowledged')
            path = '/posts/500001/like'
            self.assertEqual(request('POST', path, auth=token()), (201, {'liked': True, 'already_liked': False, 'post_id': 500001}))
            self.assertEqual(request('POST', path, auth=token()), (200, {'liked': True, 'already_liked': True, 'post_id': 500001}))
            stored = dict(post, like_count=1)
            self.assertEqual(request('GET', '/posts/500001'), (200, {'post': stored}))
            _, state = query('fixtures:writeProbeState')
            self.assertEqual(state.get('status'), 'success')
            self.assertEqual(state['value'], {'sequence': '0000000000000500001', 'extra_posts': 1})
            with MANIFEST.open('x') as output:
                json.dump({'marker': MARKER, 'acknowledged_post': stored, 'allocation_before_restart': state['value'], 'credentials_or_tokens_recorded': False}, output, indent=2)
                output.write('\n')
        else:
            recorded = json.loads(MANIFEST.read_text())
            self.assertEqual(recorded['marker'], MARKER)
            self.assertIs(recorded['credentials_or_tokens_recorded'], False)
            self.assertEqual(request('GET', '/posts/500001'), (200, {'post': recorded['acknowledged_post']}))
            _, state = query('fixtures:writeProbeState')
            self.assertEqual(state.get('status'), 'success')
            self.assertEqual(state['value'], recorded['allocation_before_restart'])
            self.assertEqual(request('POST', '/posts/500001/like', auth=token()), (200, {'liked': True, 'already_liked': True, 'post_id': 500001}))
            self.assertEqual(request('GET', '/posts/500001'), (200, {'post': recorded['acknowledged_post']}))
            status, response = request('POST', '/posts', {'body': MARKER + 'next-after-restart'}, token())
            self.assertEqual(status, 201)
            self.assertEqual(response['post']['id'], 500002, 'Persistent allocation must continue, never reset/reuse')
            self.assertEqual(response['post']['body'], MARKER + 'next-after-restart')
            self.assertGreaterEqual(response['post']['created_at'], recorded['acknowledged_post']['created_at'])
            self.assertEqual(request('GET', '/posts/500002'), (200, {'post': response['post']}))
            _, state = query('fixtures:writeProbeState')
            self.assertEqual(state.get('status'), 'success')
            self.assertEqual(state['value'], {'sequence': '0000000000000500002', 'extra_posts': 2})
            with MANIFEST.with_name(MANIFEST.stem + '-after.json').open('x') as output:
                json.dump({'acknowledged_post_after_restart': recorded['acknowledged_post'], 'next_post': response['post'], 'allocation_after_restart': state['value'], 'credentials_or_tokens_recorded': False}, output, indent=2)
                output.write('\n')
            _, cleanup = mutation('fixtures:resetWriteProbe', {'marker': MARKER})
            self.assertEqual(cleanup.get('status'), 'success', 'Cleanup refuses unexpected ownership; preserve state, no blind reseed')
            self.assertEqual(cleanup['value'], {'deleted_posts': 2, 'deleted_likes': 1})
            _, state = query('fixtures:writeProbeState')
            self.assertEqual(state.get('status'), 'success')
            self.assertEqual(state['value'], {'sequence': BASELINE, 'extra_posts': 0})


if __name__ == '__main__':
    unittest.main(verbosity=2)
