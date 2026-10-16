#!/usr/bin/env python3
"""Actual supported native application-only reset primitives on clean canonical data."""
import unittest
from convex_http_writes import mutation
from convex_feasibility import query


class NativeMaintenance(unittest.TestCase):
    def test_private_reset_primitives_exist_and_preserve_clean_canonical_state(self):
        status, result = mutation('maintenance:resetLikesPage', {'cursor': None})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success', 'Native application-only reset primitive missing')
        page = result['value']
        self.assertEqual(page['deleted'], 0)
        self.assertIs(type(page['isDone']), bool)
        self.assertIs(type(page['cursor']), str)
        status, result = mutation('maintenance:resetPostsBatch', {})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success')
        self.assertEqual(result['value'], {'deleted': 0})
        status, result = mutation('maintenance:resetAllocation', {})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success')
        self.assertEqual(result['value'], {'last_id': '0000000000000500000'})

    def test_reset_refuses_owned_edge_fixtures_outside_benchmark_range_and_time(self):
        marker = 'tds-native-edge-probe:maintenance-guard-20261015:'
        _, baseline = mutation('maintenance:resetPostsBatch', {})
        self.assertEqual(baseline.get('status'), 'success')
        self.assertEqual(baseline['value'], {'deleted': 0})
        _, installed = mutation('fixtures:installStoredEdges', {'marker': marker})
        self.assertEqual(installed.get('status'), 'success')
        try:
            _, before = query('fixtures:writeProbeState')
            self.assertEqual(before.get('status'), 'success')
            for name in ['resetPostsBatch', 'resetAllocation']:
                with self.subTest(name=name):
                    status, result = mutation('maintenance:' + name, {})
                    self.assertTrue(status >= 400 or result.get('status') == 'error', 'Unknown fixture ownership/range must refuse, never silently delete')
            _, after = query('fixtures:writeProbeState')
            self.assertEqual(after, before)
        finally:
            _, cleanup = mutation('fixtures:resetStoredEdges', {'marker': marker})
            self.assertEqual(cleanup.get('status'), 'success', 'Preserve unexpected fixture state, no blind reseed')
            self.assertEqual(cleanup['value'], {'posts_deleted': 25, 'users_deleted': 1, 'likes_deleted': 0})
        _, positive = mutation('maintenance:resetPostsBatch', {})
        self.assertEqual(positive.get('status'), 'success')
        self.assertEqual(positive['value'], {'deleted': 0})

    def test_reset_primitives_are_not_public(self):
        for name, args in [('resetLikesPage', {'cursor': None}), ('resetPostsBatch', {}), ('resetAllocation', {})]:
            with self.subTest(name=name):
                status, result = mutation('maintenance:' + name, args, authorized=False)
                self.assertTrue(status >= 400 or result.get('status') == 'error')


if __name__ == '__main__':
    unittest.main(verbosity=2)
