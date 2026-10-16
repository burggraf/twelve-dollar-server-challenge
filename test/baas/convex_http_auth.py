#!/usr/bin/env python3
"""Actual native site auth-gate regressions; rejected requests must not write data."""
import base64
import hmac
import json
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from test_api import BASE, SECRET, request, token


def signed(payload, header=None):
    encode = lambda value: base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
    text = encode(header or {'alg': 'HS256', 'typ': 'JWT'}) + '.' + encode(payload)
    return text + '.' + base64.urlsafe_b64encode(hmac.digest(SECRET, text.encode(), 'sha256')).decode().rstrip('=')


def raw_request(data):
    req = Request(BASE + '/posts', data=data, method='POST', headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token()})
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


class NativeHttpAuthGate(unittest.TestCase):
    def test_missing_bearer_precedes_post_body_and_like_id_validation(self):
        for path in ['/posts', '/posts/1/like', '/posts/not-an-id/like']:
            with self.subTest(path=path):
                self.assertEqual(request('POST', path, {'body': 'must never be stored'}),
                                 (401, {'error': 'missing bearer token'}))

    def test_malformed_bearer_precedes_post_body_and_like_id_validation(self):
        for path in ['/posts', '/posts/1/like', '/posts/not-an-id/like']:
            with self.subTest(path=path):
                self.assertEqual(request('POST', path, {'body': 'must never be stored'}, auth='not-a-jwt'),
                                 (401, {'error': 'invalid or expired token'}))

    def test_valid_signature_reaches_body_validation_but_tampering_does_not(self):
        self.assertEqual(request('POST', '/posts', {}, auth=token()), (400, {'error': 'body is required'}))
        parts = token().split('.')
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + '=' * (-len(parts[1]) % 4)))
        payload['sub'] = '2'
        parts[1] = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        self.assertEqual(request('POST', '/posts', {}, auth='.'.join(parts)), (401, {'error': 'invalid or expired token'}))
        self.assertEqual(request('POST', '/posts', {}, auth=token()), (400, {'error': 'body is required'}))

    def test_expiry_algorithm_nbf_and_malformed_claims(self):
        payload = {'sub': '1', 'username': 'golden_ember_1', 'exp': int(time.time()) + 3600}
        for extra in [{'exp': 0}, {'exp': None}, {'exp': True}, {'exp': 'future'}, {'nbf': time.time() + 3600}, {'nbf': True}]:
            with self.subTest(fields=list(extra)):
                self.assertEqual(request('POST', '/posts', {}, auth=signed(dict(payload, **extra))), (401, {'error': 'invalid or expired token'}))
        self.assertEqual(request('POST', '/posts', {}, auth=signed(payload, {'alg': 'none'})), (401, {'error': 'invalid or expired token'}))
        for sub in [0, '0', '-1', '1.0', '1e0', ' 1', '', None, True, '9223372036854775808']:
            with self.subTest(sub_type=type(sub).__name__):
                self.assertEqual(request('POST', '/posts', {}, auth=signed(dict(payload, sub=sub))), (401, {'error': 'invalid token payload'}))
        for username in [None, 5, [], {}]:
            with self.subTest(username_type=type(username).__name__):
                self.assertEqual(request('POST', '/posts', {}, auth=signed(dict(payload, username=username))), (401, {'error': 'invalid token payload'}))

    def test_valid_auth_then_body_types_trim_and_codepoint_limit(self):
        for value in [None, [], 5, 'string', {}, {'body': 5}, {'body': '\ufeff\u00a0\u2029'}]:
            with self.subTest(value_type=type(value).__name__):
                self.assertEqual(request('POST', '/posts', value, auth=token()), (400, {'error': 'body is required'}))
        self.assertEqual(request('POST', '/posts', {'body': '\U0001f600' * 501}, auth=token()), (400, {'error': 'body must be at most 500 characters'}))

    def test_strict_json_and_utf8_are_rejected_without_replacement(self):
        for raw in [b'{', b'{"body":"\\ud800"}', b'{"body":"ok","extra":{"\\udfff":"ignored"}}', b'{"body":"ok","extra":1e999}', b'{"body":"\xff"}']:
            with self.subTest(length=len(raw)):
                self.assertEqual(raw_request(raw), (400, {'error': 'malformed JSON body'}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
