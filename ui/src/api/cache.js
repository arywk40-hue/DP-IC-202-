import { CACHE_SCOPE } from './client.js';
// ─────────────────────────────────────────────────────────────────────────
// Local cache (IndexedDB) — keeps the last-known-good data visible when
// the admin device loses its WiFi link to the Master Node's AP.
// This directly implements the "live vs cached data" requirement from
// the risk analysis in the architecture report.
// ─────────────────────────────────────────────────────────────────────────

const DB_NAME = 'mesh-dashboard';
const STORE_NAME = 'snapshots';
const DB_VERSION = 1;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function cacheSet(key, value) {
  try {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).put({ value, cachedAt: Date.now() }, key);
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror = () => reject(tx.error);
    });
  } catch {
    // IndexedDB unavailable (e.g. private browsing) — fail silently,
    // dashboard just won't have an offline fallback this session.
  }
}

export async function cacheGet(key) {
  try {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).get(key);
      req.onsuccess = () => resolve(req.result ?? null);
      tx.oncomplete = () => db.close();
      req.onerror = () => reject(req.error);
    });
  } catch {
    return null;
  }
}

// Wraps any API call: try live, fall back to cache and flag staleness.
export async function withCache(key, liveFn) {
  key = `${CACHE_SCOPE}:${key}`;
  try {
    const value = await liveFn();
    await cacheSet(key, value);
    return { value, isLive: true, cachedAt: Date.now() };
  } catch (err) {
    const cached = await cacheGet(key);
    if (cached) {
      return { value: cached.value, isLive: false, cachedAt: cached.cachedAt };
    }
    throw err;
  }
}
