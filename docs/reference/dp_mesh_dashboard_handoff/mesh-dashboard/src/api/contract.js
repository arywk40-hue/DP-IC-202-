// Shared constants — keep in lockstep with Master /api/status.appVersion
// and firmware/rpc.h. See ../integration/API_CONTRACT.md (repo root).

export const DASHBOARD_API_VERSION = '0.1.0';

// LiFePO4 on the 3.3 V rail (overview §4). Display volts, never invent %.
export const BATTERY_WARN_V = 3.1;
export const BATTERY_CRIT_V = 3.0;

export const ANOMALY_LABELS = [
  'Normal',
  'Rain',
  'Thunderstorm',
  'High PM2.5',
  'Radiation Spike'
];

export function batteryLevel(volts) {
  if (volts == null || Number.isNaN(volts)) return 'unknown';
  if (volts < BATTERY_CRIT_V) return 'critical';
  if (volts < BATTERY_WARN_V) return 'warn';
  return 'ok';
}

/** Accept GeoJSON FeatureCollection or [{lat,lng,intensity}]. */
export function normalizeHeatmap(payload) {
  if (!payload) return [];
  if (Array.isArray(payload)) {
    return payload
      .filter((p) => p && typeof p.lat === 'number' && typeof p.lng === 'number')
      .map((p) => ({
        lat: p.lat,
        lng: p.lng,
        intensity: typeof p.intensity === 'number' ? p.intensity : 0.3
      }));
  }
  if (payload.type === 'FeatureCollection' && Array.isArray(payload.features)) {
    return payload.features
      .map((f) => {
        const coords = f?.geometry?.coordinates;
        if (!Array.isArray(coords) || coords.length < 2) return null;
        const [lng, lat] = coords;
        const intensity = f.properties?.intensity ?? f.properties?.value ?? 0.3;
        return { lat, lng, intensity };
      })
      .filter(Boolean);
  }
  return [];
}
