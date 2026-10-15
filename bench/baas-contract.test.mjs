import test from 'node:test';
import assert from 'node:assert/strict';
import { phaseAt, validPost, validResponse } from './baas-contract.mjs';
const post = { id: 20, body: 'hello', author: 'user', created_at: '2026-01-01T00:00:00.000Z', like_count: 0 };
test('phase boundaries exclude warmup, ramp and drain from the hold', () => {
  for (const [elapsed, phase] of [[0, 'warmup'], [149999, 'warmup'], [150000, 'ramp'], [209999, 'ramp'], [210000, 'hold'], [509999, 'hold'], [510000, 'drain']]) {
    assert.equal(phaseAt(elapsed, 30000, 120000, 60000, 300000), phase);
  }
});
test('post validation rejects malformed successful responses', () => {
  assert.equal(validPost(post), true);
  for (const bad of [null, {}, {...post, id: 0}, {...post, like_count: -1}, {...post, created_at: 'yesterday'}, {...post, body: 5}]) {
    assert.equal(Boolean(validPost(bad)), false);
  }
});
test('feed validates size, ordering, uniqueness and status', () => {
  const body = { posts: Array.from({length: 20}, (_, i) => ({...post, id: 20 - i})) };
  assert.equal(validResponse('feed', 200, body), true);
  for (const bad of [null, {}, {posts: []}, {posts: body.posts.slice().reverse()}, {posts: body.posts.map(() => post)}]) {
    assert.equal(Boolean(validResponse('feed', 200, bad)), false);
  }
  assert.equal(validResponse('feed', 500, body), false);
});
test('writes validate idempotency flags, identity and actual created content', () => {
  assert.equal(validResponse('detail', 200, {post}, {id: 20}), true);
  assert.equal(validResponse('detail', 200, {post}, {id: 21}), false);
  assert.equal(validResponse('create', 201, {post}, {body: 'hello', username: 'user'}), true);
  assert.equal(validResponse('create', 201, {post}, {body: 'wrong', username: 'user'}), false);
  assert.equal(validResponse('create', 200, {post}, {body: 'hello', username: 'user'}), false);
  for (const status of [200, 201]) {
    const body = {liked: true, already_liked: status === 200, post_id: 20};
    assert.equal(validResponse('like', status, body, {id: 20}), true);
    assert.equal(validResponse('like', status, {...body, already_liked: !body.already_liked}, {id: 20}), false);
    assert.equal(validResponse('like', status, body, {id: 21}), false);
  }
});
