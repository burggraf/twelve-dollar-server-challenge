#!/usr/bin/env python3
"""Bounded native-reset controller mechanics; actual reset/canonical proof is separate."""
import importlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))


class NativeResetController(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('convex'), 'Native reset controller missing')
        self.controller = importlib.import_module('convex')

    def test_reset_order_counts_cursor_and_persistent_allocation(self):
        responses = [
            {'cursor': 'next', 'isDone': False, 'deleted': 1.0},
            {'cursor': 'done', 'isDone': True, 'deleted': 1.0},
            {'deleted': 100.0}, {'deleted': 2.0}, {'deleted': 0.0},
            {'last_id': '0000000000000500000'},
        ]
        with patch.object(self.controller, 'mutation', side_effect=responses) as call:
            result = self.controller.reset_delta()
        self.assertEqual(result, {'like_pages': 2, 'likes_deleted': 2, 'posts_deleted': 102, 'sequence_last_id': '0000000000000500000'})
        self.assertEqual(call.call_args_list[0].args, ('maintenance:resetLikesPage', {'cursor': None}))
        self.assertEqual(call.call_args_list[1].args, ('maintenance:resetLikesPage', {'cursor': 'next'}))
        self.assertEqual(call.call_args_list[-1].args, ('maintenance:resetAllocation', {}))

    def test_cursor_cycle_fails_without_post_or_allocation_reset(self):
        with patch.object(self.controller, 'mutation', return_value={'cursor': 'same', 'isDone': False, 'deleted': 0}) as call:
            with self.assertRaises(RuntimeError): self.controller.reset_delta()
        self.assertEqual(call.call_count, 2)
        self.assertTrue(all(c.args[0] == 'maintenance:resetLikesPage' for c in call.call_args_list))

    def test_invalid_batch_shapes_and_counts_fail_closed(self):
        for response in [None, {}, {'cursor': 'x', 'isDone': 1, 'deleted': 0}, {'cursor': 'x', 'isDone': True, 'deleted': True}, {'cursor': 'x', 'isDone': True, 'deleted': 1001}, {'cursor': 'x', 'isDone': True, 'deleted': 0.5}]:
            with self.subTest(response=response), patch.object(self.controller, 'mutation', return_value=response):
                with self.assertRaises(RuntimeError): self.controller.reset_delta()

    def test_nonempty_post_batch_failure_does_not_reset_allocation(self):
        with patch.object(self.controller, 'mutation', side_effect=[{'cursor': 'done', 'isDone': True, 'deleted': 0}, {'deleted': -1}]) as call:
            with self.assertRaises(RuntimeError): self.controller.reset_delta()
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args_list[-1].args[0], 'maintenance:resetPostsBatch')

    def test_native_admin_headers_cannot_follow_redirects_to_another_origin(self):
        self.assertTrue(hasattr(self.controller, '_NoRedirect'), 'Native administrator transport needs an explicit no-redirect policy')
        handler = self.controller._NoRedirect()
        self.assertIsNone(handler.redirect_request(None, None, 302, 'Found', {}, 'http://unrelated.invalid/'))

    def test_private_environment_and_url_credentials_never_enter_error_messages(self):
        key = 'synthetic-admin-never-echo'
        for url in ['http://name:synthetic-password@backend:3210', 'http://backend:3210?synthetic-private-query=1', 'http://backend:3210#synthetic-fragment']:
            with self.subTest(url=url), patch.dict(os.environ, {'CONVEX_SELF_HOSTED_URL': url, 'CONVEX_SELF_HOSTED_ADMIN_KEY': key}, clear=True):
                with self.assertRaises((ValueError, RuntimeError)) as caught:
                    self.controller.mutation('maintenance:resetAllocation', {})
                text = str(caught.exception)
                for value in [key, url, 'synthetic-password', 'synthetic-private-query', 'synthetic-fragment']:
                    self.assertNotIn(value, text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
