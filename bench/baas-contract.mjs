// Pure workload validation/phase helpers, also exercised by Node's built-in tests.
export function phaseAt(elapsed, warmRamp, warmHold, ramp, hold) {
  const start = warmRamp + warmHold + ramp;
  return elapsed < warmRamp + warmHold ? 'warmup' : elapsed < start ? 'ramp' : elapsed < start + hold ? 'hold' : 'drain';
}
const timestamp = /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/;
export function validPost(post) {
  return Boolean(post && Number.isSafeInteger(post.id) && post.id > 0 && typeof post.body === 'string'
    && typeof post.author === 'string' && typeof post.created_at === 'string' && timestamp.test(post.created_at)
    && Number.isSafeInteger(post.like_count) && post.like_count >= 0);
}
export function validResponse(endpoint, status, body, expected = {}) {
  if (endpoint === 'feed') {
    if (status !== 200 || !body || !Array.isArray(body.posts) || body.posts.length !== 20 || !body.posts.every(validPost)) return false;
    return new Set(body.posts.map(p => p.id)).size === 20 && body.posts.every((p, i, all) => !i
      || all[i - 1].created_at > p.created_at || (all[i - 1].created_at === p.created_at && all[i - 1].id > p.id));
  }
  if (endpoint === 'detail') return Boolean(status === 200 && body && validPost(body.post) && body.post.id === expected.id);
  if (endpoint === 'create') return Boolean(status === 201 && body && validPost(body.post)
    && body.post.body === expected.body && body.post.author === expected.username && body.post.like_count === 0);
  if (endpoint === 'like') return Boolean((status === 200 || status === 201) && body && body.liked === true
    && body.already_liked === (status === 200) && body.post_id === expected.id);
  return false;
}
