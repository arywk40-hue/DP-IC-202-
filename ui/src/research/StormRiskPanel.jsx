import React, { useEffect, useState } from 'react';
import { getStormReport, getStormScores, getStormHeatmap } from '../api/client';

export default function StormRiskPanel() {
  const [report, setReport] = useState(null);
  const [rows, setRows] = useState([]);
  const [feature, setFeature] = useState('');
  const [map, setMap] = useState(null);
  const [error, setError] = useState(null);
  useEffect(() => {
    let active = true;
    Promise.all([getStormReport(), getStormScores()]).then(([r,s]) => {
      if (!active) return;
      setReport(r); setRows(s.rows || []);
      setFeature(r.heatmaps?.features?.[0] || '');
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    let active = true; setMap(null);
    if (feature) getStormHeatmap(feature).then(m => { if (active) setMap(m); }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [feature]);
  return <details className="storm-risk-panel">
    <summary>ERA5 storm-risk research · {report?.configured ? report.run_id : 'No run loaded'}</summary>
    {error && <p role="alert">Research outputs unavailable: {error}</p>}
    {!report?.configured && <p>Select a local research run when starting the backend. Sensor telemetry is shown separately below.</p>}
    {report?.configured && <>
      <p><strong>{report.evidence_kind === 'synthetic_engineering' ? 'SYNTHETIC ENGINEERING DEMO' : 'Retrospective gridded research'}</strong> · {report.target?.name} · {report.target?.lead_hours === 0 ? 'Current-hour assessment' : `${report.target?.lead_hours}-hour horizon`}</p>
      <p>{report.calibrated ? 'Mapped ensemble passed the configured held-out gate.' : 'Experimental risk score (uncalibrated)'}</p>
      <p>Calibration gate: {report.calibrated ? 'passed' : 'not passed'} · Run status: {report.status}</p>
      {report.gate_failures?.length > 0 && <ul aria-label="Gate conditions">{report.gate_failures.map(w => <li key={w}>{w}</li>)}</ul>}
      {report.warnings?.length > 0 && <details><summary>Run warnings ({report.warnings.length})</summary><ul>{report.warnings.map((w,i) => <li key={i}>{w}</li>)}</ul></details>}
      {report.ensemble_weights && <p>Ensemble weights: {Object.entries(report.ensemble_weights).map(([k,v]) => `${k} ${v.toFixed(2)}`).join(' · ')}</p>}
      <p>Grid agreement is spatially correlated context, separate from physical-node corroboration.</p>
      <div className="storm-table-wrap"><table aria-label="Storm research cells"><thead><tr><th scope="col">Cell / time</th><th scope="col">Ensemble score</th><th scope="col">Anomaly markers</th><th scope="col">Neighbour-confirmed (experimental)</th></tr></thead>
        <tbody>{rows.map((r,i) => <tr key={i}><td>{r.lat}, {r.lon}<br />{r.time}</td><td>{Number.isFinite(r.ensemble_risk_uncal ?? r.ensemble_cal_prob) ? (r.ensemble_risk_uncal ?? r.ensemble_cal_prob).toFixed(3) : 'Unavailable'}</td><td>{r.anomaly_available === false ? 'Climatology unavailable' : r.anomaly_flag ? r.anomaly_features : 'No flagged feature'}</td><td>{r.neighbour_confirmed ? 'Confirmed (experimental)' : 'Not confirmed'}</td></tr>)}</tbody></table></div>
      {report.heatmaps?.features?.length > 0 && <label>Feature heatmap <select value={feature} onChange={e => setFeature(e.target.value)}>{report.heatmaps.features.map(f => <option key={f}>{f}</option>)}</select></label>}
      {map?.values && <FeatureGrid map={map} rows={rows} />}
    </>}
  </details>;
}

function FeatureGrid({map, rows}) {
  const finite = map.values.flat().filter(Number.isFinite);
  if (!finite.length) return <p>No supported feature cells.</p>;
  const low = Math.min(...finite), high = Math.max(...finite);
  return <figure className="storm-feature-grid"><svg viewBox={`0 0 ${map.lon.length} ${map.lat.length}`} role="img" aria-label={`${map.feature} feature heatmap`}>
    {map.values.flatMap((row,y) => row.map((value,x) => <rect key={`${x}:${y}`} x={x} y={map.lat.length-1-y} width="1" height="1" fill={Number.isFinite(value) ? `hsl(${240-((value-low)/(high-low || 1))*220} 65% 50%)` : '#445'}><title>{map.lat[y]}, {map.lon[x]}: {value ?? 'Unavailable'}</title></rect>))}
    {rows.filter(r => r.time === map.time && (r.anomaly_flag || r.neighbour_confirmed)).map((r,i) => {
      const x = map.lon.indexOf(r.lon), y = map.lat.indexOf(r.lat);
      return x < 0 || y < 0 ? null : <circle key={`marker-${i}`} data-testid="anomaly-marker" cx={x+.5} cy={map.lat.length-y-.5} r=".18" stroke={r.anomaly_flag ? '#ff3355' : '#ffcc44'} strokeWidth=".08" fill="none"><title>{r.anomaly_flag ? `Anomaly: ${r.anomaly_features}` : 'Neighbour-confirmed (experimental)'}</title></circle>;
    })}
  </svg><figcaption>{map.feature}: {low.toFixed(2)}–{high.toFixed(2)} {map.unit} · {map.time}<br />Original ERA5 grid · {map.evidence_kind} · Longitude left to right; latitude bottom to top.<br />Red rings: feature anomalies. Gold rings: neighbour-confirmed (experimental).</figcaption></figure>;
}
