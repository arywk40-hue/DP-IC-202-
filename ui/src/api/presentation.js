export function locationName(node) {
  if (!node) return "Select a location";
  const name = node.name || node.id || "";
  if (name === "mandi-api-current") return "Mandi";
  return name;
}
export function sourceName(source) {
  return (
    {
      modeled_grid: "Mandi modeled data",
      physical_sensor: "Your ESP32 sensor",
    }[source] || "Source unavailable"
  );
}
export function readingTime(value) {
  if (!value) return "Waiting for a reading";
  return (
    new Intl.DateTimeFormat("en-IN", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "Asia/Kolkata",
    }).format(new Date(value)) + " IST"
  );
}
export function ageLabel(value) {
  const minutes = Math.max(0, Math.floor((Date.now() - value) / 60000));
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes} min ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} hr ago`;
  return `${Math.floor(minutes / 1440)} days ago`;
}

export function formatSignalQuality(rssi) {
  if (rssi == null || !Number.isFinite(rssi)) {
    return { bars: 0, label: "No Signal", level: "none", color: "#64748b" };
  }
  if (rssi >= -65) {
    return { bars: 4, label: "Excellent", level: "excellent", color: "#10b981" };
  }
  if (rssi >= -75) {
    return { bars: 3, label: "Good", level: "good", color: "#34d399" };
  }
  if (rssi >= -85) {
    return { bars: 2, label: "Fair", level: "fair", color: "#f59e0b" };
  }
  return { bars: 1, label: "Weak", level: "weak", color: "#ef4444" };
}

export function formatBatteryEstimate(voltage) {
  if (voltage == null || !Number.isFinite(voltage)) {
    return { pct: null, hoursLeft: null, status: "Unknown", color: "#64748b" };
  }
  const clamped = Math.max(3.0, Math.min(4.2, voltage));
  const pct = Math.round(((clamped - 3.2) / (4.2 - 3.2)) * 100);
  const boundedPct = Math.max(0, Math.min(100, pct));
  const hoursLeft = Math.round((boundedPct / 100) * 24);
  const status = boundedPct > 50 ? "Healthy" : boundedPct > 20 ? "Moderate" : "Low";
  const color = boundedPct > 50 ? "#10b981" : boundedPct > 20 ? "#f59e0b" : "#ef4444";
  return { pct: boundedPct, hoursLeft, status, color };
}

export function formatAirQualityIndex(pm25) {
  if (pm25 == null || !Number.isFinite(pm25)) {
    return { label: "Unavailable", category: "none", color: "#64748b" };
  }
  if (pm25 <= 30) return { label: "Good", category: "good", color: "#10b981" };
  if (pm25 <= 60) return { label: "Moderate", category: "moderate", color: "#38bdf8" };
  if (pm25 <= 90) return { label: "Unhealthy for Sensitive", category: "sensitive", color: "#f59e0b" };
  if (pm25 <= 120) return { label: "Poor", category: "poor", color: "#f97316" };
  return { label: "Severe", category: "severe", color: "#ef4444" };
}

export function formatElevationComparison(baro_m, gps_m) {
  const hasBaro = baro_m != null && Number.isFinite(baro_m);
  const hasGps = gps_m != null && Number.isFinite(gps_m);
  if (!hasBaro && !hasGps) return { delta: null, note: "No altitude data" };
  if (!hasBaro) return { delta: null, note: `GPS only (${gps_m.toFixed(0)}m)` };
  if (!hasGps) return { delta: null, note: `Barometric only (${baro_m.toFixed(0)}m)` };
  const delta = Math.round(baro_m - gps_m);
  const note = Math.abs(delta) < 20 ? "In agreement (±20m)" : `Variance ${delta > 0 ? "+" : ""}${delta}m`;
  return { delta, note };
}
