#!/usr/bin/env python3
"""Actual native transactions; namespace-bounded cleanup is opt-in and private."""
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from convex_feasibility import BASE, query
from test_api import request, token

MARKER = os.environ.get('CONVEX_WRITE_PROBE_MARKER', 'tds-native-write-probe:default:')
BASELINE = '0000000000000500000'


def mutation(path, args, authorized=True):
    headers = {'Content-Type': 'application/json'}
    if authorized:
        headers['Authorization'] = 'Convex ' + os.environ['CONVEX_SELF_HOSTED_ADMIN_KEY']
    req = Request(BASE + '/api/mutation', data=json.dumps({'path': path, 'args': args, 'format': 'json'}).encode(), headers=headers)
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as response:
        return response.code, json.load(response)


class NativeHttpWrites(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        if os.environ.get('CONVEX_PROBE_CLEANUP') == '1':
            status, result = mutation('fixtures:resetWriteProbe', {'marker': MARKER})
            if status != 200 or result.get('status') != 'success':
                raise AssertionError('Private namespace-bounded probe cleanup failed; preserve state and inspect, never blindly reseed')
            status, result = query('fixtures:writeProbeState')
            if status != 200 or result.get('value') != {'sequence': BASELINE, 'extra_posts': 0}:
                raise AssertionError('Canonical allocation/post range not restored by bounded native cleanup')

    def probe_state(self):
        status, result = query('fixtures:writeProbeState')
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success', 'Private native allocation state primitive missing')
        return result['value']

    def create(self, suffix, *, subject=None):
        status, data = request('POST', '/posts', {'body': MARKER + suffix}, auth=subject or token())
        self.assertEqual(status, 201, 'Native compatibility create did not return 201')
        self.assertEqual(list(data), ['post'])
        self.assertEqual(list(data['post']), ['id', 'body', 'created_at', 'author', 'like_count'])
        self.assertIs(type(data['post']['id']), int)
        self.assertEqual(data['post']['like_count'], 0)
        return data['post']

    def test_01_private_empty_probe_reset_and_current_sequence(self):
        status, result = mutation('fixtures:resetWriteProbe', {'marker': MARKER})
        self.assertEqual(status, 200)
        self.assertEqual(result.get('status'), 'success', 'Private bounded native cleanup primitive missing')
        self.assertEqual(result.get('value'), {'deleted_posts': 0, 'deleted_likes': 0})
        self.assertEqual(query('fixtures:writeProbeState')[1].get('value'), {'sequence': BASELINE, 'extra_posts': 0})

    def test_02_create_unicode_nul_and_signed_author_then_native_read(self):
        post = self.create('café\x00😀', subject=token(username='signed-claim-name'))
        self.assertEqual(post['id'], 500001)
        self.assertEqual(post['author'], 'signed-claim-name')
        self.assertEqual(post['body'], MARKER + 'café\x00😀')
        self.assertRegex(post['created_at'], r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$')
        status, actual = request('GET', '/posts/' + str(post['id']))
        self.assertEqual(status, 200)
        self.assertEqual(actual['post']['body'], post['body'])
        self.assertEqual(actual['post']['created_at'], post['created_at'])
        # The creation response uses signed username; reads join stored users.
        self.assertNotEqual(actual['post']['author'], 'signed-claim-name')

    def test_03_concurrent_duplicate_like_is_exactly_once(self):
        post = self.create('duplicate-like')
        path = '/posts/' + str(post['id']) + '/like'
        with ThreadPoolExecutor(max_workers=32) as pool:
            responses = list(pool.map(lambda _: request('POST', path, auth=token()), range(32)))
        self.assertEqual([status for status, _ in responses].count(201), 1)
        self.assertEqual([status for status, _ in responses].count(200), 31)
        for status, value in responses:
            self.assertEqual(list(value), ['liked', 'already_liked', 'post_id'])
            self.assertEqual(value, {'liked': True, 'already_liked': status == 200, 'post_id': post['id']})
        self.assertEqual(request('GET', '/posts/' + str(post['id']))[1]['post']['like_count'], 1)
        self.assertEqual(request('POST', path, auth=token(sub='2', username='ignored-like-name'))[0], 201)
        self.assertEqual(request('GET', '/posts/' + str(post['id']))[1]['post']['like_count'], 2)

    def test_04_concurrent_post_allocation_is_unique_and_contiguous(self):
        before = int(self.probe_state()['sequence'])
        with ThreadPoolExecutor(max_workers=16) as pool:
            posts = list(pool.map(lambda i: self.create('parallel-' + str(i)), range(32)))
        self.assertEqual(sorted(post['id'] for post in posts), list(range(before + 1, before + 33)))
        feed = request('GET', '/feed')[1]['posts']
        self.assertEqual(len(feed), 20)
        self.assertEqual([(p['created_at'], p['id']) for p in feed], sorted([(p['created_at'], p['id']) for p in posts], reverse=True)[:20])

    def test_05_missing_user_rolls_back_without_consuming_post_id(self):
        before = self.probe_state()['sequence']
        self.assertEqual(request('POST', '/posts', {'body': MARKER + 'must-rollback'}, auth=token(sub='9223372036854775807')), (500, {'error': 'internal server error'}))
        self.assertEqual(self.probe_state()['sequence'], before)
        self.assertEqual(self.create('after-rollback')['id'], int(before) + 1)

    def test_06_trim_500_codepoints_and_id_auth_precedence(self):
        body = MARKER + '😀' * (500 - len(MARKER))
        status, response = request('POST', '/posts', {'body': '\ufeff\u2003' + body + '\u2029'}, auth=token())
        self.assertEqual(status, 201)
        self.assertEqual(response['post']['body'], body)
        self.assertEqual(request('POST', '/posts/not-an-id/like', auth=token()), (400, {'error': 'invalid post id'}))
        self.assertEqual(request('POST', '/posts/9223372036854775807/like', auth=token()), (404, {'error': 'post not found'}))

    def test_07_private_mutations_and_cleanup_are_not_anonymous(self):
        for path, args in [('native:createPost', {'userId': '0000000000000000001', 'body': MARKER + 'must-not-be-stored'}), ('native:likePost', {'userId': '0000000000000000001', 'postId': '0000000000000000001'}), ('fixtures:resetWriteProbe', {'marker': MARKER})]:
            with self.subTest(path=path):
                status, value = mutation(path, args, authorized=False)
                self.assertTrue(status >= 400 or value.get('status') == 'error', 'Native privileged mutation exposed anonymously')


if __name__ == '__main__':
    unittest.main(verbosity=2)
