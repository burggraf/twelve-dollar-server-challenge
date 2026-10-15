// BaaS workload v1. No app-specific paths beyond the common HTTP contract.
import http from 'k6/http';
import exec from 'k6/execution';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { Rate, Gauge } from 'k6/metrics';
import { phaseAt, validResponse } from './baas-contract.mjs';

const BASE = __ENV.BASE_URL || 'http://trailbase:4000';
const VUS = Number(__ENV.VUS || 2500);
const smoke = __ENV.SMOKE === '1';
const warmRamp = smoke ? 0 : 30;
const warmHold = smoke ? 0 : 120;
const ramp = smoke ? 5 : 60;
const hold = smoke ? 20 : 300;
const drain = smoke ? 5 : 30;
const warmVus = smoke ? 0 : Math.min(1000, VUS);
const tokens = new SharedArray('identities', () => JSON.parse(open(__ENV.TOKENS || '/tokens.json')));
const scenarioStart = new Gauge('benchmark_scenario_start_ms');
const errors = new Rate('request_errors');
const schemaErrors = new Rate('schema_errors');
const thresholds = {
  'http_req_duration{phase:hold}': ['p(95)<500', 'p(99)<1000'],
  'request_errors{phase:hold}': ['rate<0.01'],
  'schema_errors{phase:hold}': ['rate==0'],
  'http_reqs{phase:hold}': ['count>0'],
};
for (const endpoint of ['feed', 'detail', 'like', 'create']) {
  // Always-pass thresholds request per-endpoint summary submetrics; not extra scoring rules.
  thresholds[`http_req_duration{phase:hold,endpoint:${endpoint}}`] = ['max>=0'];
  thresholds[`request_errors{phase:hold,endpoint:${endpoint}}`] = ['rate<=1'];
  thresholds[`http_reqs{phase:hold,endpoint:${endpoint}}`] = ['count>=0'];
}
export const options = {
  scenarios: { users: { executor: 'ramping-vus', startVUs: 0,
    stages: [
      ...(smoke ? [] : [{ duration: `${warmRamp}s`, target: warmVus }, { duration: `${warmHold}s`, target: warmVus }]),
      { duration: `${ramp}s`, target: VUS }, { duration: `${hold}s`, target: VUS }, { duration: `${drain}s`, target: 0 },
    ], gracefulRampDown: '10s', gracefulStop: '10s',
  } },
  thresholds,
  summaryTrendStats: ['avg', 'med', 'p(95)', 'p(99)', 'min', 'max'],
  systemTags: ['status', 'method', 'name', 'scenario', 'error_code', 'expected_response'],
  maxRedirects: 0,
};
const between = (lo, hi) => lo + Math.random() * (hi - lo);
const currentPhase = () => phaseAt(Date.now() - exec.scenario.startTime, warmRamp * 1000, warmHold * 1000, ramp * 1000, hold * 1000);
function request(endpoint, method, path, data, auth, expected = {}) {
  const tags = { phase: currentPhase(), endpoint, name: `${method} ${endpoint}` };
  const response = http.request(method, BASE + path, data, { headers: auth || {}, tags, timeout: '10s' });
  let body = null;
  try { body = response.json(); } catch (_) { /* Invalid JSON is a measured failure, not a crashed VU. */ }
  const valid = validResponse(endpoint, response.status, body, expected);
  errors.add(!valid, tags);
  const successfulStatus = endpoint === 'create' ? response.status === 201 : endpoint === 'like'
    ? response.status === 200 || response.status === 201 : response.status === 200;
  schemaErrors.add(successfulStatus && !valid, tags);
  check(response, { 'contract-valid response': () => valid }, tags);
  return valid ? body : null;
}
export default function () {
  const user = tokens[(__VU - 1) % tokens.length];
  const auth = { Authorization: `Bearer ${user.token}`, 'Content-Type': 'application/json' };
  if (__ITER === 0) {
    scenarioStart.add(exec.scenario.startTime);
    sleep(between(0, 5));
  }
  const feed = request('feed', 'GET', '/feed', null, null);
  if (!feed) { sleep(between(3, 7)); return; }
  const post = feed.posts[Math.floor(Math.random() * feed.posts.length)];
  sleep(between(3, 7));
  request('detail', 'GET', `/posts/${post.id}`, null, null, {id: post.id});
  sleep(between(3, 8));
  if (Math.random() < 0.15) request('like', 'POST', `/posts/${post.id}/like`, null, auth, {id: post.id});
  if (Math.random() < 0.02) {
    const body = `${user.username} says hi at ${new Date().toISOString()} (VU ${__VU}, iter ${__ITER})`;
    request('create', 'POST', '/posts', JSON.stringify({body}), auth, {body, username: user.username});
  }
  sleep(between(5, 15));
}
export function handleSummary(data) {
  data.benchmark = { workload: 'baas-v1', vus: VUS, mode: smoke ? 'smoke' : 'capacity', hold_seconds: hold,
    warmup_vus: warmVus, warmup_ramp_seconds: warmRamp, warmup_seconds: warmHold, ramp_seconds: ramp, drain_seconds: drain };
  return { [__ENV.SUMMARY || '/runs/k6-summary.json']: JSON.stringify(data, null, 2) + '\n' };
}
