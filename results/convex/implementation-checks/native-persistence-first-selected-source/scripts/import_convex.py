#!/usr/bin/env python3
"""Prepare supported JSONLines inputs; never opens Convex's underlying storage.

Public positive signed64 identities use 19-digit decimal text so native index
ordering is numeric without JavaScript-number loss. Native imports supply their
own extra _id/_creationTime. Only a completely verified export becomes visible.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import tempfile

from import_sqlite import EXPECTED_COUNTS, EXPECTED_HASH

COLUMNS = {
    'users': ('id', 'username', 'created_at'),
    'posts': ('id', 'user_id', 'body', 'created_at'),
    'likes': ('user_id', 'post_id', 'created_at'),
}


def identity(value):
    if not re.fullmatch(r'[1-9][0-9]*', value) or int(value) > 9223372036854775807:
        raise ValueError('Noncanonical positive signed64 identity')
    return int(value)


def export_jsonl(source, destination, *, expected_counts=EXPECTED_COUNTS, expected_hash=EXPECTED_HASH):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError('Refusing to replace existing native JSONLines inputs')
    digest = hashlib.sha256()
    counts, users, posts, usernames = {}, set(), set(), set()
    maximum_post_id, maximum_likes = 0, 0
    with tempfile.TemporaryDirectory(prefix='convex-jsonl-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        for table, columns in COLUMNS.items():
            count, previous_id, group_post, group_rows, group_users = 0, 0, 0, [], set()

            def finish_likes_group():
                for row in sorted(group_rows, key=lambda row: int(row[0])):
                    digest.update(('|'.join(row) + '\n').encode('utf-8'))

            with (source / (table + '.tsv')).open(newline='', encoding='utf-8') as stream, (stage / (table + '.jsonl')).open('w', encoding='utf-8', newline='\n') as output:
                for row in csv.reader(stream, delimiter='\t', quoting=csv.QUOTE_NONE):
                    if len(row) != len(columns):
                        raise ValueError('Unexpected canonical TSV column count: ' + table)
                    values = dict(zip(columns, row))
                    if table != 'likes':
                        number = identity(values['id'])
                        if number <= previous_id:
                            raise ValueError('Public identities must be unique and numerically ordered')
                        previous_id = number
                        if table == 'users':
                            if values['username'] in usernames:
                                raise ValueError('Duplicate logical username')
                            users.add(number)
                            usernames.add(values['username'])
                        else:
                            if identity(values['user_id']) not in users:
                                raise ValueError('Post references missing logical user')
                            posts.add(number)
                            maximum_post_id = number
                        digest.update(('|'.join(row) + '\n').encode('utf-8'))
                    else:
                        user, post = identity(values['user_id']), identity(values['post_id'])
                        if user not in users or post not in posts:
                            raise ValueError('Like references missing logical user/post')
                        if post < group_post:
                            raise ValueError('Likes must be ordered by logical post')
                        if post != group_post:
                            finish_likes_group()
                            maximum_likes = max(maximum_likes, len(group_rows))
                            group_post, group_rows, group_users = post, [], set()
                        if user in group_users:
                            raise ValueError('Duplicate logical user/post like')
                        group_users.add(user)
                        group_rows.append(row)
                    for key in ['id', 'user_id', 'post_id']:
                        if key in values:
                            values[key] = str(identity(values[key])).zfill(19)
                    output.write(json.dumps(values, ensure_ascii=False, separators=(',', ':')) + '\n')
                    count += 1
                if table == 'likes':
                    finish_likes_group()
                    maximum_likes = max(maximum_likes, len(group_rows))
            counts[table] = count
            if count != expected_counts[table]:
                raise ValueError('Canonical logical row count differs: ' + table)
        if digest.hexdigest() != expected_hash:
            raise ValueError('Canonical logical content hash mismatch')
        if maximum_post_id == 0:
            raise ValueError('Canonical post allocation metadata requires seeded posts')
        (stage / 'feed_sequences.jsonl').write_text(json.dumps({'name': 'posts', 'last_id': str(maximum_post_id).zfill(19)}, separators=(',', ':')) + '\n')
        if destination.exists():
            raise FileExistsError('Native JSONLines destination appeared during preparation')
        stage.rename(destination)
    return {'counts': counts, 'content_sha256': digest.hexdigest(),
            'max_likes_per_post': maximum_likes,
            'public_id_mapping': 'Positive signed64 decimal text, zero-padded to 19 digits',
            'next_post_id': maximum_post_id + 1,
            'files': {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(destination.iterdir())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    manifest = export_jsonl(args.source, args.destination)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
