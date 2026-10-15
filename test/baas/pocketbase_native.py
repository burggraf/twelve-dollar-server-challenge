"""Real PocketBase REST/storage permissions and compatibility-identity boundary."""
import unittest
from urllib.parse import urlencode

import test_api as app


class NativePocketBase(unittest.TestCase):
    def test_native_record_storage_and_request_time_count_match_common_api(self):
        status, common = app.request('GET', '/posts/500000')
        self.assertEqual(status, 200)
        status, native = app.request('GET', '/api/collections/feed_posts/records/500000')
        self.assertEqual(status, 200, native)
        self.assertEqual(native['id'], '500000')
        self.assertEqual(native['body'], common['post']['body'])
        self.assertEqual(native['created_at'], common['post']['created_at'])
        self.assertIsInstance(native['user_id'], str)
        query = urlencode({'perPage': 1, 'filter': 'post_id="500000"'})
        status, likes = app.request('GET', '/api/collections/feed_likes/records?' + query)
        self.assertEqual(status, 200, likes)
        self.assertEqual(likes['totalItems'], common['post']['like_count'])

    def test_direct_native_application_writes_are_locked(self):
        forged = app.token(role='superuser', collectionId='_superusers', id='untrusted', type='auth')
        operations = [
            ('POST', '/api/collections/feed_users/records', {'id': '999999', 'username': 'forged', 'created_at': '2026-01-01T00:00:00.000Z'}),
            ('POST', '/api/collections/feed_posts/records', {'id': '999999', 'user_id': '1', 'body': 'forged', 'created_at': '2026-01-01T00:00:00.000Z'}),
            ('POST', '/api/collections/feed_likes/records', {'user_id': '1', 'post_id': '500000', 'created_at': '2026-01-01T00:00:00.000Z'}),
            ('PATCH', '/api/collections/feed_posts/records/500000', {'body': 'forged'}),
            ('DELETE', '/api/collections/feed_posts/records/500000', app.UNSET),
            ('PATCH', '/api/collections/feed_sequences/records/feedpostcounter', {'last_id': '0'}),
        ]
        for auth in [None, app.token(), forged]:
            for method, path, body in operations:
                with self.subTest(method=method, path=path, compat=auth is not None):
                    status, result = app.request(method, path, body, auth)
                    self.assertIn(status, [401, 403, 404], result)

    def test_native_sequence_metadata_is_not_publicly_readable(self):
        for path in ['/api/collections/feed_sequences/records',
                     '/api/collections/feed_sequences/records/feedpostcounter']:
            for auth in [None, app.token()]:
                status, result = app.request('GET', path, auth=auth)
                self.assertIn(status, [401, 403, 404], result)

    def test_signed_subject_not_arbitrary_role_or_user_claim_controls_native_owner(self):
        token = app.token(sub='1', username='verbatim signed name', role='superuser', app_user_id='2', user_id='2')
        status, result = app.request('POST', '/posts', {'body': 'native ownership boundary'}, token)
        self.assertEqual(status, 201, result)
        post = result['post']
        self.assertEqual(post['author'], 'verbatim signed name')
        status, native = app.request('GET', '/api/collections/feed_posts/records/' + str(post['id']))
        self.assertEqual(status, 200, native)
        self.assertEqual(native['user_id'], '1')
        status, read = app.request('GET', '/posts/' + str(post['id']))
        self.assertEqual(status, 200, read)
        self.assertEqual(read['post']['author'], 'golden_ember_1')

    def test_native_and_common_unicode_nul_storage_are_lossless(self):
        text = '\u0085binary-safe \x00 café 😀'
        status, result = app.request('POST', '/posts', {'body': text}, app.token())
        self.assertEqual(status, 201, result)
        post = result['post']
        self.assertEqual(post['body'], text)
        self.assertEqual(app.request('GET', '/posts/' + str(post['id'])), (200, {'post': post}))
        status, native = app.request('GET', '/api/collections/feed_posts/records/' + str(post['id']))
        self.assertEqual(status, 200, native)
        self.assertEqual(native['body'], text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
