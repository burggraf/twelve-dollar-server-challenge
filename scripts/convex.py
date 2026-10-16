#!/usr/bin/env python3
"""Untimed supported native Convex application-delta reset. No SQL/Docker driver.

Run only with no application writers, in the owned tools namespace. A complete
native canonical hash and platform/private-input preservation check is required
AFTER reset; deletion counts alone never certify restoration. No retries.
"""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request
import uuid

BASELINE = '0000000000000500000'
MAX_LIKE_PAGES = 5000
MAX_POST_BATCHES = 10000
MUTATIONS = {'maintenance:resetLikesPage', 'maintenance:resetPostsBatch', 'maintenance:resetAllocation'}


def _failure(raw=None, status=None):
    # Full failed native response stays PRIVATE, never in console/errors or args.
    directory = os.environ.get('CONVEX_RESET_ERROR_DIRECTORY')
    if directory and raw is not None:
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True, mode=0o700)
        if target.is_symlink():
            raise RuntimeError('Unsafe private native error directory')
        prefix = 'native-reset-error-' + uuid.uuid4().hex
        fd = os.open(target / (prefix + '.original'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as output: output.write(raw)
        fd = os.open(target / (prefix + '.json'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            json.dump({'http_status': status, 'raw_response_retained_privately': True, 'request_headers_or_credentials_recorded': False}, output)
            output.write('\n')
    raise RuntimeError('Native maintenance request failed; preserve current state') from None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def mutation(path, args):
    if path not in MUTATIONS or not isinstance(args, dict):
        raise ValueError('Unsupported native maintenance request')
    url = os.environ.get('CONVEX_SELF_HOSTED_URL', '')
    key = os.environ.get('CONVEX_SELF_HOSTED_ADMIN_KEY', '')
    try:
        endpoint = urllib.parse.urlsplit(url)
        safe_target = (endpoint.hostname == 'backend' and endpoint.port == 3210) or (endpoint.hostname in ['127.0.0.1', 'localhost'] and endpoint.port == 13210)
        valid = endpoint.scheme == 'http' and safe_target and not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment and endpoint.path in ['', '/']
    except ValueError:
        valid = False
    if not valid or not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
        raise ValueError('Invalid owned native administrator environment') from None
    request = urllib.request.Request(url.rstrip('/') + '/api/mutation', data=json.dumps({'path': path, 'args': args, 'format': 'json'}, allow_nan=False).encode(), headers={'Content-Type': 'application/json', 'Authorization': 'Convex ' + key}, method='POST')
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect()).open(request, timeout=30) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as error:
        _failure(error.read(), error.code)
    except (urllib.error.URLError, ValueError):
        _failure()
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        _failure(raw, status)
    if not isinstance(value, dict) or value.get('status') != 'success' or 'value' not in value:
        _failure(raw, status)
    return value['value']


def _count(value, maximum):
    if type(value) not in [int, float] or not 0 <= value <= maximum or int(value) != value:
        raise RuntimeError('Invalid bounded native reset count; preserve state')
    return int(value)


def reset_delta():
    cursor = None
    seen = set()
    likes_deleted = posts_deleted = 0
    for page_number in range(1, MAX_LIKE_PAGES + 1):
        page = mutation('maintenance:resetLikesPage', {'cursor': cursor})
        if not isinstance(page, dict) or set(page) != {'cursor', 'isDone', 'deleted'} or type(page['isDone']) is not bool or type(page['cursor']) is not str:
            raise RuntimeError('Invalid native reset page; preserve state')
        likes_deleted += _count(page['deleted'], 1000)
        if page['isDone']:
            break
        cursor = page['cursor']
        if not cursor or cursor in seen:
            raise RuntimeError('Nonprogressing native reset cursor; preserve state')
        seen.add(cursor)
    else:
        raise RuntimeError('Native like reset safety bound exceeded; preserve state')
    for _ in range(MAX_POST_BATCHES):
        batch = mutation('maintenance:resetPostsBatch', {})
        if not isinstance(batch, dict) or set(batch) != {'deleted'}:
            raise RuntimeError('Invalid native post reset batch; preserve state')
        deleted = _count(batch['deleted'], 100)
        posts_deleted += deleted
        if deleted == 0:
            break
    else:
        raise RuntimeError('Native post reset safety bound exceeded; preserve state')
    sequence = mutation('maintenance:resetAllocation', {})
    if sequence != {'last_id': BASELINE}:
        raise RuntimeError('Native reset allocation mismatch; preserve state')
    return {'like_pages': page_number, 'likes_deleted': likes_deleted, 'posts_deleted': posts_deleted, 'sequence_last_id': BASELINE}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['reset'])
    parser.parse_args()
    print(json.dumps(reset_delta(), sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
