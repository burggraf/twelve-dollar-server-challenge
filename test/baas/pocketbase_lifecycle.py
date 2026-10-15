"""Embedded DB transport-stop/recovery and actual process-restart persistence.

This is a normal restart, not a provider power-loss/storage-durability test.
Real native connection-close 503/500 and transaction rollback are separate Go tests.
"""
import json
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.request import urlopen

import test_api as app

STATE = Path('/state/pocketbase/persistence.json')


def prepare():
    body = 'acknowledged restart persistence \x00 café 😀'
    status, result = app.request('POST', '/posts', {'body': body}, app.token())
    assert status == 201, result
    post = result['post']
    status, like = app.request('POST', f'/posts/{post["id"]}/like', auth=app.token())
    assert status == 201 and like['already_liked'] is False, like
    post['like_count'] = 1
    STATE.write_text(json.dumps(post) + '\n')
    print('ACKNOWLEDGED_NATIVE_POST_AND_EXACTLY_ONCE_LIKE_PREPARED')


def stopped():
    try:
        with urlopen(app.BASE + '/health', timeout=3) as response:
            raise AssertionError('Stopped embedded server still returned HTTP ' + str(response.status))
    except (URLError, TimeoutError, ConnectionError):
        pass
    print('STOPPED_OWNED_EMBEDDED_SERVER_TRANSPORT_UNAVAILABLE')


def verify():
    post = json.loads(STATE.read_text())
    assert app.request('GET', f'/posts/{post["id"]}') == (200, {'post': post})
    status, native = app.request('GET', '/api/collections/feed_posts/records/' + str(post['id']))
    assert status == 200 and native['body'] == post['body'] and native['user_id'] == '1'
    assert app.request('POST', f'/posts/{post["id"]}/like', auth=app.token()) == (
        200, {'liked': True, 'already_liked': True, 'post_id': post['id']})
    status, result = app.request('POST', '/posts', {'body': 'post-restart allocation'}, app.token())
    assert status == 201 and result['post']['id'] > post['id'], result
    print('REAL_NATIVE_PROCESS_RESTART_PRESERVES_ACKNOWLEDGED_POST_LIKE_AND_ID_SEQUENCE')


if __name__ == '__main__':
    commands = {'prepare': prepare, 'stopped': stopped, 'verify': verify}
    commands[sys.argv[1]]()
