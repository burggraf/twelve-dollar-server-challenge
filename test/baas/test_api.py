"""Backend-neutral black-box regressions. Run after the inherited suite on a disposable seed.

BASE_URL and JWT_SECRET configure the target. No third-party test dependencies.
"""
import base64
from concurrent.futures import ThreadPoolExecutor
import hmac
import json
import os
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = os.environ.get('BASE_URL', 'http://127.0.0.1:4000').rstrip('/')
SECRET = os.environ.get('JWT_SECRET', 'twelve-dollar-challenge').encode()
UNSET = object()


def token(sub='1', username='golden_ember_1', **extra):
    def b64(value):
        return base64.urlsafe_b64encode(value).decode().rstrip('=')
    payload = dict(sub=sub, username=username, exp=int(time.time()) + 3600, **extra)
    text = b64(b'{"alg":"HS256","typ":"JWT"}') + '.' + b64(json.dumps(payload).encode())
    return text + '.' + b64(hmac.digest(SECRET, text.encode(), 'sha256'))


def request(method, path, data=UNSET, auth=None):
    headers = {'Content-Type': 'application/json'}
    if auth is not None:
        headers['Authorization'] = 'Bearer ' + auth
    req = Request(BASE + path, data=None if data is UNSET else json.dumps(data).encode(),
                  headers=headers, method=method)
    try:
        response = urlopen(req, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        raw = response.read()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {'_non_json': raw.decode(errors='replace')}
        return response.status, body


class FeedContract(unittest.TestCase):
    def create(self, body='concurrency regression', auth=None):
        status, result = request('POST', '/posts', {'body': body}, auth or token())
        self.assertEqual(status, 201, result)
        return result['post']

    def test_storage_health(self):
        status, body = request('GET', '/health')
        self.assertEqual(status, 200)
        self.assertEqual((body['status'], body['db']), ('ok', 'ok'))
        self.assertIsInstance(body['uptime_s'], int)

    def test_concurrent_duplicate_likes_commit_once(self):
        post = self.create()
        def like(_):
            return request('POST', f'/posts/{post["id"]}/like', auth=token())
        with ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(like, range(32)))
        self.assertEqual(sorted(status for status, _ in results), [200] * 31 + [201])
        self.assertEqual(sum(not body['already_liked'] for _, body in results), 1)
        self.assertTrue(all(body['liked'] and body['post_id'] == post['id'] for _, body in results))
        self.assertEqual(request('GET', f'/posts/{post["id"]}')[1]['post']['like_count'], 1)

    def test_concurrent_post_ids_and_immediate_reads(self):
        def create(i):
            status, body = request('POST', '/posts', {'body': f'parallel {i}'}, token())
            self.assertEqual(status, 201, body)
            post = body['post']
            self.assertEqual(request('GET', f'/posts/{post["id"]}'), (200, {'post': post}))
            return post['id']
        with ThreadPoolExecutor(max_workers=16) as pool:
            ids = list(pool.map(create, range(32)))
        self.assertEqual(len(set(ids)), 32)
        posts = request('GET', '/feed')[1]['posts']
        keys = [(post['created_at'], post['id']) for post in posts]
        self.assertEqual(keys, sorted(keys, reverse=True))
        self.assertEqual(len(posts), 20)

    def test_unicode_limits_and_ecmascript_trim(self):
        body = '😀' * 500
        self.assertEqual(self.create('\ufeff\u00a0' + body + '\u2029')['body'], body)
        self.assertEqual(request('POST', '/posts', {'body': body + '😀'}, token()),
                         (400, {'error': 'body must be at most 500 characters'}))
        self.assertEqual(request('POST', '/posts', {'body': '\ufeff\u00a0\u2029'}, token()),
                         (400, {'error': 'body is required'}))
        for value in [None, [], 5, 'string']:
            self.assertEqual(request('POST', '/posts', value, token()),
                             (400, {'error': 'body is required'}))

    def test_identity_is_bound_to_signed_subject(self):
        post = self.create()
        path = f'/posts/{post["id"]}/like'
        forged = token(sub='2', username='untrusted-name')
        parts = forged.split('.')
        # Alter a signed subject without recomputing the signature.
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
        payload['sub'] = '3'
        parts[1] = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        self.assertEqual(request('POST', path, auth='.'.join(parts)),
                         (401, {'error': 'invalid or expired token'}))
        self.assertEqual(request('GET', f'/posts/{post["id"]}')[1]['post']['like_count'], 0)
        self.assertEqual(request('POST', path, auth=token())[0], 201)
        self.assertEqual(request('POST', path, auth=forged)[0], 201)
        self.assertEqual(request('GET', f'/posts/{post["id"]}')[1]['post']['like_count'], 2)
        self.assertEqual(request('POST', path, auth=forged)[0], 200)

    def test_strict_jwt_payload_and_expiry(self):
        for sub in [0, '0', '-1', '1.0', '1e0', ' 1', '', None, True]:
            self.assertEqual(request('POST', '/posts', {'body': 'reject'}, token(sub=sub)),
                             (401, {'error': 'invalid token payload'}))
        for username in [None, 5, [], {}]:
            self.assertEqual(request('POST', '/posts', {'body': 'reject'}, token(username=username)),
                             (401, {'error': 'invalid token payload'}))
        for exp in [None, 'future', True, 0]:
            # Construct separately because token() normally sets exp.
            header, payload, _ = token().split('.')
            obj = {'sub': '1', 'username': 'golden_ember_1', 'exp': exp}
            payload = base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip('=')
            text = header + '.' + payload
            signature = base64.urlsafe_b64encode(hmac.digest(SECRET, text.encode(), 'sha256')).decode().rstrip('=')
            self.assertEqual(request('POST', '/posts', {'body': 'reject'}, text + '.' + signature),
                             (401, {'error': 'invalid or expired token'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
