import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeHeatmap, batteryLevel } from '../src/api/contract.js';
import { sendRpc, RpcTimeoutError, getNodes } from '../src/api/client.js';

test('missing spatial uncertainty/data never becomes a made-up intensity', () => {
  assert.deepEqual(normalizeHeatmap({ type: 'FeatureCollection', features: [{ geometry: { coordinates: [76,31] }, properties: {} }] }), []);
  assert.deepEqual(normalizeHeatmap([{lat:31,lng:76,intensity:NaN}]), []);
  assert.equal(batteryLevel(null), 'unknown');
});
test('HTTP accepted/queued is not a physical ACK and API failure never creates mocks', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ queued: true }) });
    await assert.rejects(sendRpc('one',1), RpcTimeoutError);
    globalThis.fetch = async () => { throw new Error('Offline'); };
    await assert.rejects(getNodes(), /Offline/);
  } finally { globalThis.fetch = original; }
});
