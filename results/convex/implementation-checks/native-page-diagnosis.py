#!/usr/bin/env python3
"""Bounded read-only page tracing; original helper/30s deadline unchanged."""
import hashlib
import json
import sys
import time

sys.path.insert(0, '/work/test/baas')
from convex_feasibility import query

for table in ['users', 'posts', 'likes']:
    cursor = None
    for number in range(1, 4):
        started = time.monotonic()
        context = {'table': table, 'page': number, 'cursor_sha256': hashlib.sha256((cursor or '').encode()).hexdigest()}
        print(json.dumps({'event': 'begin', **context}), flush=True)
        try:
            status, result = query('native:canonicalPage', {'table': table, 'cursor': cursor})
            record = {'event': 'end', **context, 'elapsed_s': time.monotonic()-started, 'http_status': status, 'native_status': result.get('status')}
            if result.get('status') != 'success':
                record['error_message'] = result.get('errorMessage')
                print(json.dumps(record), flush=True)
                break
            value = result['value']
            record.update({'rows': len(value['page']), 'is_done': value['isDone']})
            print(json.dumps(record), flush=True)
            if value['isDone']:
                break
            cursor = value['continueCursor']
        except Exception as error:
            print(json.dumps({'event': 'exception', **context, 'elapsed_s': time.monotonic()-started, 'exception_type': type(error).__name__}), flush=True)
            break
