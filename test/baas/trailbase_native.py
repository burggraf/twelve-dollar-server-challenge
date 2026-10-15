"""TrailBase-specific Record API, health failure injection, and restart persistence checks.

Run in the tooling container with /depot mounted. Mutations are confined to the
benchmark app's tables. The serving implementation itself never opens SQLite directly.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import unittest
from test_api import request, token

STATE = Path('/state/trailbase/restart-probe.json')


def run(after_restart):
    case = unittest.TestCase()
    if after_restart:
        expected = json.loads(STATE.read_text())
        case.assertEqual(request('GET', f'/posts/{expected["id"]}'), (200, {'post': expected}))
        print('PASS: acknowledged post and like survive a real container restart')
        return
    status, record = request('GET', '/api/records/v1/benchmark_posts/500000')
    case.assertEqual(status, 200, record)
    case.assertEqual(record['id'], 500000)
    case.assertEqual(record['body'], request('GET', '/posts/500000')[1]['post']['body'])
    status, body = request('POST', '/api/records/v1/benchmark_posts', {'user_id': 1, 'body': 'forbidden'})
    case.assertIn(status, [401, 403], body)
    print('PASS: native read-only Record API sees the canonical data and denies direct writes')

    status, result = request('POST', '/posts', {'body': 'restart durability probe'}, token())
    case.assertEqual(status, 201, result)
    post = result['post']
    case.assertEqual(request('POST', f'/posts/{post["id"]}/like', auth=token())[0], 201)
    post['like_count'] = 1
    case.assertEqual(request('GET', f'/posts/{post["id"]}'), (200, {'post': post}))
    STATE.write_text(json.dumps(post) + '\n')

    # Fault injection outside the timed workload. Restore even when the assertion fails.
    with sqlite3.connect('/depot/data/main.db') as conn:
        conn.execute('ALTER TABLE users RENAME TO users_unreachable')
        conn.commit()
        try:
            status, health = request('GET', '/health')
            case.assertEqual(status, 503, health)
            case.assertEqual((health['status'], health['db']), ('degraded', 'unreachable'))
        finally:
            conn.execute('ALTER TABLE users_unreachable RENAME TO users')
            conn.commit()
    case.assertEqual(request('GET', '/health')[0], 200)
    print('PASS: storage-probe failure returns 503 and recovers after storage restoration')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--after-restart', action='store_true')
    run(parser.parse_args().after_restart)
