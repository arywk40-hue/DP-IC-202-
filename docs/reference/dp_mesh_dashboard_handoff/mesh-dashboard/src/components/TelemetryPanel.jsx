import React from 'react';
import { batteryLevel } from '../api/contract';

const SENSOR_LABELS = {
  temperature_c: ['Temp (BME680)', '°C'],
  humidity_pct: ['Humidity', '%'],
  pressure_hpa: ['Pressure', 'hPa'],
  voc_iaq: ['VOC / IAQ', ''],
  wind_speed_ms: ['Wind speed', 'm/s'],
  wind_dir_deg: ['Wind vane', '°'],
  rain_mm: ['Rain (tips)', 'mm'],
  pm25_ugm3: ['PM2.5', 'µg/m³'],
  pm10_ugm3: ['PM10', 'µg/m³'],
  uv_index: ['UV index', ''],
  radiation_cpm: ['Radiation', 'CPM'],
  lightning_km: ['Lightning', 'km'],
  soil_temp_c: ['Soil temp', '°C'],
  soil_rh_pct: ['Soil moisture', '%']
};

function fmt(value) {
  if (value == null) return '—';
  if (typeof value === 'number' && !Number.isInteger(value)) return value.toFixed(1);
  return value;
}

export default function TelemetryPanel({ nodeName, telemetry, loading, onOpenRpc }) {
  if (!nodeName) {
    return (
      <div className="telemetry-panel telemetry-empty">
        Select a node on the map or list to inspect the 11-sensor array.
      </div>
    );
  }

  return (
    <div className="telemetry-panel">
      <div className="panel-title row-title">
        {nodeName}
        {onOpenRpc && (
          <button type="button" className="rpc-send-btn" onClick={onOpenRpc}>
            Send RPC…
          </button>
        )}
      </div>

      {loading && <div className="telemetry-loading">Loading…</div>}

      {!loading && telemetry && (
        <>
          <div className={`anomaly-banner anomaly-${telemetry.anomalyIndex > 0 ? 'alert' : 'ok'}`}>
            {telemetry.anomalyIndex > 0
              ? `TinyML anomaly: ${telemetry.anomalyLabel} (index ${telemetry.anomalyIndex})`
              : 'Normal — XGBoost index 0'}
          </div>

          <div className="sensor-grid">
            {Object.entries(SENSOR_LABELS).map(([key, [label, unit]]) => (
              <div key={key} className="sensor-cell">
                <span className="sensor-label">{label}</span>
                <span className="sensor-value">
                  {fmt(telemetry.sensors?.[key])}
                  {unit && telemetry.sensors?.[key] != null && (
                    <span className="sensor-unit">{unit}</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          <div className={`telemetry-footer batt-${batteryLevel(telemetry.battery)}`}>
            LiFePO4 pack: {telemetry.battery.toFixed(2)} V
            {batteryLevel(telemetry.battery) === 'warn' && ' — low (< 3.10 V)'}
            {batteryLevel(telemetry.battery) === 'critical' && ' — critical (< 3.00 V)'}
          </div>
        </>
      )}
    </div>
  );
}
