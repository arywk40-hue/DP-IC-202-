import React from 'react';
import { batteryLevel } from '../api/contract';

const CHANNELS = {
  temperature_c: ['Temperature', '°C'], relative_humidity_pct: ['Relative humidity', '%'],
  pressure_hpa: ['Station / grid pressure', 'hPa'], pm25_ug_m3: ['PM2.5', 'µg/m³'],
  pm10_ug_m3: ['PM10', 'µg/m³'], wind_speed_mps: ['Wind speed', 'm/s']
};
const fmt = (v) => Number.isFinite(v) ? v.toFixed(1) : 'Unavailable';
const date = (v) => v ? new Date(v).toLocaleString() : 'Unknown';

function History({ rows, channel }) {
  const finite = rows.map((r,i) => ({ i, value: r[channel] })).filter(p => Number.isFinite(p.value));
  if (finite.length < 2) return <small>Insufficient history</small>;
  const low = Math.min(...finite.map(p => p.value));
  const high = Math.max(...finite.map(p => p.value));
  // Preserve gaps: no line segment crosses a missing sensor sample.
  const segments = []; let segment = [];
  rows.forEach((r,i) => {
    if (!Number.isFinite(r[channel])) { if (segment.length) segments.push(segment); segment=[]; }
    else segment.push(`${(i/(rows.length-1))*180},${36-(r[channel]-low)/(high-low || 1)*30}`);
  });
  if (segment.length) segments.push(segment);
  return <svg viewBox="0 0 180 40" role="img" aria-label={`${CHANNELS[channel][0]} recent observations`}>
    {segments.map((points,i) => <polyline key={i} points={points.join(' ')} fill="none" stroke="currentColor" strokeWidth="1.5" />)}
  </svg>;
}

export default function TelemetryPanel({ nodeName, telemetry, loading, cached, rpcAvailable, onOpenRpc }) {
  if (!nodeName) return <div className="telemetry-panel telemetry-empty">No observations loaded. Import six-channel snapshots or start the labelled demo.</div>;
  return <section className="telemetry-panel" aria-label="Node telemetry">
    <div className="panel-title row-title">{nodeName}
      {rpcAvailable && onOpenRpc && <button className="rpc-send-btn" onClick={onOpenRpc}>Send RPC…</button>}
    </div>
    {loading && <p>Loading…</p>}
    {!loading && !telemetry && <p>Telemetry unavailable.</p>}
    {!loading && telemetry && <>
      <div className="research-banner source-banner">
        <strong>{telemetry.syntheticDemo ? 'SYNTHETIC DEMO' : telemetry.sourceClass}</strong><br />
        Observation: {date(telemetry.timestamp)}<br />
        {(cached || telemetry.stale) && <strong className="stale-notice">{cached ? 'CACHED · ' : ''}STALE / HISTORICAL — not a current warning<br /></strong>}
        Source: {telemetry.sourceId}<br />Pressure: {telemetry.pressureReference}
      </div>
      <div className="sensor-grid">
        {Object.entries(CHANNELS).map(([key,[label,unit]]) => <div className="sensor-cell" key={key}>
          <span className="sensor-label">{label}</span>
          <span className="sensor-value">{fmt(telemetry.sensors?.[key])} <span className="sensor-unit">{unit}</span></span>
          <History rows={telemetry.history || []} channel={key} />
          <span className="forecast-value">+6h estimate: {fmt(telemetry.forecast6h?.[key])} {unit}</span>
        </div>)}
      </div>
      <p className="evidence-note">Forecast for {date(telemetry.forecastTimestamp)}<br />
        Model: {telemetry.forecastModel?.id}. Trained on Mandi-location modeled grids; field accuracy unverified.
      </p>
      <h3>Experimental risk assessments</h3>
      <p className="evidence-note">Current sensor patterns, not six-hour event forecasts. Scores are not probabilities. A non-match does not establish safety.</p>
      {Object.values(telemetry.risks || {}).map((risk) => <article key={risk.target} className={`risk-card risk-${risk.abstain ? 'unknown' : risk.level}`}>
        <h4>{risk.display_name}</h4>
        <strong>{risk.abstain ? 'Unknown / insufficient evidence' : risk.level.replaceAll('_',' ')}</strong>
        <div>Rule score: {Number.isFinite(risk.score) ? `${risk.score.toFixed(2)} / 1` : 'Unavailable'} · Evidence coverage: {Math.round(risk.coverage*100)}%</div>
        <div>Probability: unavailable · Peer corroboration: {risk.corroboration}</div>
        <details><summary>Rule evidence ({risk.triggered_evidence.length} matched)</summary>
          <ul>{risk.evidence.map(e => <li key={e.feature}>{e.feature}: {e.value == null ? 'Unavailable' : String(e.value)} {e.unit} — {e.matched == null ? 'unknown' : e.matched ? 'matched' : 'not matched'}</li>)}</ul>
          <small>{risk.profile} · {risk.confidence_kind}</small>
        </details>
      </article>)}
      <p className="evidence-note">Storm sequence: {telemetry.stormSequence?.matched == null ? 'Unavailable / incomplete native history' : telemetry.stormSequence.matched ? 'Experimental sequence matched' : 'Sequence not matched'}.<br />
        Flash flood and landslide predictors: unavailable. Public alerts disabled; human review required.</p>
      <div className={`telemetry-footer batt-${batteryLevel(telemetry.battery)}`}>
        Battery: {Number.isFinite(telemetry.battery) ? `${telemetry.battery.toFixed(2)} V` : 'Not measured'}
      </div>
    </>}
  </section>;
}
