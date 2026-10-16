#!/usr/bin/env python3
"""Actual owned PostgreSQL-down health probe; orchestrator must always recover it."""
import json
import os
from pathlib import Path
import time
import unittest
from urllib.error import URLError

from test_api import request


class NativeDependencyFailure(unittest.TestCase):
    def test_actual_stopped_postgres_is_sanitized_degraded_health(self):
        started = time.monotonic()
        try:
            status, body = request('GET', '/health')
            observed = {'status': status, 'body': body, 'elapsed_seconds': time.monotonic() - started}
        except (URLError, TimeoutError, ConnectionError) as error:
            observed = {'status': None, 'exception_type': type(error).__name__, 'elapsed_seconds': time.monotonic() - started}
        if os.environ.get('CONVEX_DEPENDENCY_PROBE_MANIFEST'):
            with Path(os.environ['CONVEX_DEPENDENCY_PROBE_MANIFEST']).open('x') as stream:
                json.dump(observed, stream, indent=2)
                stream.write('\n')
        self.assertEqual(observed['status'], 503, 'Actual dependency-down health must return503, not stale success, generic500 or a dead endpoint')
        body = observed['body']
        self.assertEqual(list(body), ['status', 'db', 'error'])
        self.assertEqual((body['status'], body['db']), ('degraded', 'unreachable'))
        self.assertIsInstance(body['error'], str)
        self.assertNotIn('postgres', body['error'].lower())
        self.assertNotIn('password', body['error'].lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
