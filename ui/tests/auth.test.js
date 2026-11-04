import test from 'node:test';
import assert from 'node:assert/strict';
import { getAuthConfig, authWithGoogle, authDemo, getAuthMe, authLogout } from '../src/api/client.js';

test('auth API helpers correctly format requests', async () => {
  const original = globalThis.fetch;
  const calls = [];
  try {
    globalThis.fetch = async (url, options = {}) => {
      calls.push({ url, options });
      if (url.endsWith('/api/auth/config')) {
        return { ok: true, json: async () => ({ googleClientId: 'mock-client-id', authEnabled: true }) };
      }
      if (url.endsWith('/api/auth/demo-login')) {
        return { ok: true, json: async () => ({ token: 'mock-token', user: { email: 'ariyan@test.org' } }) };
      }
      if (url.endsWith('/api/auth/me')) {
        return { ok: true, json: async () => ({ user: { email: 'ariyan@test.org', name: 'Ariyan' } }) };
      }
      if (url.endsWith('/api/auth/logout')) {
        return { ok: true, json: async () => ({ ok: true }) };
      }
      return { ok: true, json: async () => ({}) };
    };

    const cfg = await getAuthConfig();
    assert.equal(cfg.googleClientId, 'mock-client-id');

    const loginRes = await authDemo();
    assert.equal(loginRes.token, 'mock-token');
    assert.deepEqual(calls.find((call) => call.url.endsWith('/api/auth/demo-login')).options.body, '{}');

    const me = await getAuthMe();
    assert.equal(me.user.name, 'Ariyan');

    const logoutRes = await authLogout();
    assert.equal(logoutRes.ok, true);
  } finally {
    globalThis.fetch = original;
  }
});
