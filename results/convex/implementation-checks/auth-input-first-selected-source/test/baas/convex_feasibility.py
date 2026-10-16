#!/usr/bin/env python3
"""Real self-hosted native API/cache smoke gate; run only on designated VPS."""
import json
import os
import re
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.environ.get('CONVEX_SELF_HOSTED_URL', 'http://backend:3210')


def query(path, args=None, authorized=True):
    headers = {'Content-Type': 'application/json'}
    if authorized:
        headers['Authorization'] = 'Convex ' + os.environ['CONVEX_SELF_HOSTED_ADMIN_KEY']
    request = Request(BASE + '/api/query', data=json.dumps({'path': path, 'args': args or {}, 'format': 'json'}).encode(), headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as response:
        return response.code, json.load(response)


def metrics():
    with urlopen(BASE + '/metrics', timeout=15) as response:
        text = response.read().decode()
    def total(suffix):
        values = re.findall(r'^\w*' + re.escape(suffix) + r'(?:\{[^\n]*\})?\s+([0-9.eE+\-]+)$', text, re.MULTILINE)
        return sum(map(float, values))
    return {name: total(name) for name in ['cache_plan_go_total', 'cache_plan_ready_total', 'cache_plan_wait_total', 'cache_size_bytes']}


class NativeFeasibility(unittest.TestCase):
    def test_01_native_database_probe(self):
        status, result = query('native:storageProbe')
        self.assertEqual(status, 200, 'Native storage query unavailable')
        self.assertEqual(result.get('status'), 'success', 'native:storageProbe missing or failed')
        self.assertEqual(result.get('value'), {'users': [], 'posts': [], 'likes': []})

    def test_02_native_probe_is_not_a_public_query(self):
        status, result = query('native:storageProbe', authorized=False)
        self.assertTrue(status >= 400 or result.get('status') == 'error', 'Internal storage function exposed to unauthenticated callers')

    def test_03_identical_queries_reexecute_without_result_cache(self):
        before = metrics()
        for _ in range(5):
            status, result = query('native:storageProbe')
            self.assertEqual(status, 200, 'Native storage query unavailable')
            self.assertEqual(result.get('status'), 'success', 'Native storage query failed')
        after = metrics()
        self.assertGreaterEqual(after['cache_plan_go_total'] - before['cache_plan_go_total'], 5, 'Repeated native queries did not execute')
        self.assertEqual(after['cache_plan_ready_total'], before['cache_plan_ready_total'], 'Native query result cache hit')
        self.assertEqual(after['cache_plan_wait_total'], before['cache_plan_wait_total'], 'Native shared result wait/cache hit')
        self.assertEqual(after['cache_size_bytes'], 0, 'Native query cache retained data')


if __name__ == '__main__':
    unittest.main(verbosity=2)
