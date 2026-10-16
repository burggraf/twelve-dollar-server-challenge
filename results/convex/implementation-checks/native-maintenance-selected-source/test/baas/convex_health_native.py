#!/usr/bin/env python3
"""Native backend clock/private-action gate, executed only on designated Linux VPS."""
from datetime import datetime
import json
import os
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.environ.get('CONVEX_SELF_HOSTED_URL', 'http://backend:3210')


def clock(authorized=True):
    headers = {'Content-Type': 'application/json'}
    if authorized:
        headers['Authorization'] = 'Convex ' + os.environ['CONVEX_SELF_HOSTED_ADMIN_KEY']
    request = Request(BASE + '/api/action', data=json.dumps({'path': 'clock:backendUptime', 'args': {}, 'format': 'json'}).encode(), headers=headers)
    try:
        response = urlopen(request, timeout=30)
    except HTTPError as error:
        response = error
    with response:
        return response.status, json.load(response)


class NativeHealthClock(unittest.TestCase):
    def test_backend_uptime_matches_actual_container_process_start(self):
        started = datetime.fromisoformat(os.environ['CONVEX_TEST_BACKEND_STARTED_AT'].replace('Z', '+00:00')).timestamp()
        previous = -1
        for _ in range(2):
            before = time.time() - started
            status, value = clock()
            after = time.time() - started
            self.assertEqual(status, 200, 'Native clock action unavailable')
            self.assertEqual(value.get('status'), 'success', 'Native backend clock action missing or failed')
            uptime = value['value']
            self.assertIsInstance(uptime, (int, float))
            self.assertNotIsInstance(uptime, bool)
            self.assertEqual(uptime, int(uptime))
            self.assertGreaterEqual(uptime, 0)
            self.assertGreaterEqual(uptime, before - 3, 'Clock is not actual backend-process uptime')
            self.assertLessEqual(uptime, after + 3, 'Clock is not actual backend-process uptime')
            self.assertGreaterEqual(uptime, previous)
            previous = uptime

    def test_clock_action_is_not_public(self):
        status, value = clock(authorized=False)
        self.assertTrue(status >= 400 or value.get('status') == 'error', 'Native diagnostic action exposed publicly')


if __name__ == '__main__':
    unittest.main(verbosity=2)
