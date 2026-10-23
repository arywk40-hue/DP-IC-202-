// Keep in lockstep with the Python adapter's /api/status.appVersion.
// The original teammate firmware contract is preserved separately in docs/reference/.

export const DASHBOARD_API_VERSION = '0.5.0';

// LiFePO4 on the 3.3 V rail (overview §4). Display volts, never invent %.
export const BATTERY_WARN_V = 3.1;
export const BATTERY_CRIT_V = 3.0;

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
      .filter((p) => p && Number.isFinite(p.lat) && Number.isFinite(p.lng) && Number.isFinite(p.intensity))
      .map((p) => ({
        lat: p.lat,
        lng: p.lng,
        intensity: p.intensity
      }));
  }
  if (payload.type === 'FeatureCollection' && Array.isArray(payload.features)) {
    return payload.features
      .map((f) => {
        const coords = f?.geometry?.coordinates;
        if (!Array.isArray(coords) || coords.length < 2) return null;
        const [lng, lat] = coords;
        const intensity = f.properties?.intensity ?? f.properties?.value ?? null;
        return Number.isFinite(lat) && Number.isFinite(lng) && Number.isFinite(intensity) ? { lat, lng, intensity } : null;
      })
      .filter(Boolean);
  }
  return [];
}
