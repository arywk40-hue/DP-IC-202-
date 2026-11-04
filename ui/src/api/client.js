// INDRA adapter integration. No silent fallback to invented live readings.
import { DASHBOARD_API_VERSION, normalizeHeatmap } from './contract.js';

export const MASTER_BASE_URL = (import.meta.env?.VITE_MASTER_BASE_URL ?? '').replace(/\/$/, '');
export const CACHE_SCOPE = `${DASHBOARD_API_VERSION}:${MASTER_BASE_URL || 'same-origin'}`;
async function request(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const headers = { ...options.headers };
    if (typeof localStorage !== 'undefined') {
      const token = localStorage.getItem('indra_auth_token');
      if (token && !headers['Authorization']) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }
    const res = await fetch(`${MASTER_BASE_URL}${path}`, { ...options, headers, signal: controller.signal, cache: 'no-store' });
    if (!res.ok) throw new Error(`INDRA API ${res.status}: ${await res.text()}`);
    return await res.json();
  } catch (error) {
    if (options.method === 'POST' && error.name === 'AbortError') throw new Error('Request timed out');
    throw error;
  } finally { clearTimeout(timer); }
}
export const getProvenance = () => request('/api/provenance');
export const getNodes = () => request('/api/nodes');
export const getStatus = () => request('/api/status');
export const getModelLab = () => request('/api/model-lab');
export const getTelemetry = (id) => request(`/api/nodes/${encodeURIComponent(id)}/telemetry`);
export const getAllParameterMaps = () => request('/api/parameter-heatmaps');
export const getHeatmap = async (channel='temperature_c') => {
  const payload = await request(`/api/kriging/heatmap?channel=${encodeURIComponent(channel)}`);
  return { ...payload, points: normalizeHeatmap(payload) };
};
export const getAuthConfig = () => request('/api/auth/config');
export const authWithGoogle = (credential) => request('/api/auth/google', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ credential })
});
export const authDemo = () => request('/api/auth/demo-login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({})
});
export const getAuthMe = () => request('/api/auth/me');
export const authLogout = () => request('/api/auth/logout', { method: 'POST' });

// Pan-India National Mesh & Multi-Zone Forecasting APIs
export const getNationalZones = () => request('/api/national/zones');
export const getNationalStations = (zone = '', query = '', limit = 50) => {
  const params = new URLSearchParams();
  if (zone) params.set('zone', zone);
  if (query) params.set('query', query);
  if (limit) params.set('limit', String(limit));
  const qs = params.toString();
  return request(`/api/national/stations${qs ? '?' + qs : ''}`);
};
export const getNationalForecast = (lat = 31.71, lon = 76.93, locationName = '') => {
  const params = new URLSearchParams();
  params.set('lat', String(lat));
  params.set('lon', String(lon));
  if (locationName) params.set('location_name', locationName);
  return request(`/api/national/forecast?${params.toString()}`);
};

// Jaipur & Arid Northwest Windstorm & Dust Hazards APIs
export const getJaipurWindRisk = (windSpeedMps = 25.5, pm10 = 1650.0, tempC = 30.5) => {
  const params = new URLSearchParams();
  params.set('wind_speed_mps', String(windSpeedMps));
  params.set('pm10_ug_m3', String(pm10));
  params.set('temp_c', String(tempC));
  return request(`/api/national/jaipur/wind-risk?${params.toString()}`);
};
export const getJaipurScenarios = () => request('/api/national/jaipur/scenarios');
export const getJaipurSimulate = (scenario = 'andhi_dust_storm', draws = 512) => {
  const params = new URLSearchParams();
  params.set('scenario', scenario);
  params.set('draws', String(draws));
  return request(`/api/national/jaipur/simulate?${params.toString()}`);
};
