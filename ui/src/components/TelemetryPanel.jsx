import React from "react";
import WeatherCategories from "./WeatherCategories";
import HazardScenarios from "./HazardScenarios";
import { readingTime, sourceName } from "../api/presentation";
const CHANNELS = {
  temperature_c: ["Temperature", "°C"],
  relative_humidity_pct: ["Humidity", "%"],
  pressure_hpa: ["Pressure", "hPa"],
  pm25_ug_m3: ["PM2.5", "µg/m³"],
  pm10_ug_m3: ["PM10", "µg/m³"],
  wind_speed_mps: ["Wind", "m/s"],
};
const fmt = (v) => (Number.isFinite(v) ? v.toFixed(1) : "—");
function History({ rows, channel }) {
  const finite = rows.map((r) => r[channel]).filter(Number.isFinite);
  if (finite.length < 2) return <div className="history-empty" />;
  const low = Math.min(...finite),
    high = Math.max(...finite);
  const segments = [];
  let segment = [];
  rows.forEach((r, i) => {
    if (!Number.isFinite(r[channel])) {
      if (segment.length) segments.push(segment);
      segment = [];
    } else
      segment.push(
        `${(i / (rows.length - 1)) * 180},${36 - ((r[channel] - low) / (high - low || 1)) * 28}`,
      );
  });
  if (segment.length) segments.push(segment);
  return (
    <svg
      viewBox="0 0 180 40"
      role="img"
      aria-label={`${CHANNELS[channel][0]} recent observations`}
    >
      {segments.map((v, i) => (
        <polyline
          key={i}
          points={v.join(" ")}
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
        />
      ))}
    </svg>
  );
}
export function TechnicalDetails({ telemetry: t, rpcAvailable, onOpenRpc }) {
  if (!t)
    return (
      <p className="empty-message">
        Select a location to see its data details.
      </p>
    );
  return (
    <section className="technical-details">
      <div className="section-heading">
        <h2>Location details</h2>
        <code>{t.id}</code>
      </div>
      <dl className="detail-list">
        <div>
          <dt>Data source</dt>
          <dd>{sourceName(t.sourceClass)}</dd>
        </div>
        <div>
          <dt>Source identity</dt>
          <dd>{t.sourceId}</dd>
        </div>
        <div>
          <dt>Observed</dt>
          <dd>{readingTime(t.timestamp)}</dd>
        </div>
        <div>
          <dt>Pressure reference</dt>
          <dd>{t.pressureReference}</dd>
        </div>
        <div>
          <dt>Forecast model</dt>
          <dd>
            {t.forecastModel?.displayName}
            <br />
            <code>{t.forecastModel?.id}</code>
          </dd>
        </div>
        <div>
          <dt>Forecast state</dt>
          <dd>
            {t.forecastStatus} · {t.forecastHistoryRows ?? 0}/
            {t.forecastHistoryRequired ?? 25} hourly readings
          </dd>
        </div>
        <div>
          <dt>Forecast endpoint</dt>
          <dd>{readingTime(t.forecastTimestamp)}</dd>
        </div>
      </dl>
      <p className="evidence-note">
        Forecasting uses Mandi modeled grids for training. Field accuracy is not
        established. Pattern classification uses simulated scenarios and has no
        calibrated real-event probabilities.
      </p>
      {t.forecastModel?.blendWeights && (
        <details className="forecast-components">
          <summary>Forecast model components</summary>
          <ul>
            {Object.entries(t.forecastModel.blendWeights).map(([key, head]) => (
              <li key={key}>
                {CHANNELS[key]?.[0]}:{" "}
                {Object.entries(head.weights)
                  .filter(([, v]) => v > 0.0001)
                  .map(([k, v]) => `${k} ${v.toFixed(2)}`)
                  .join(" · ")}
              </li>
            ))}
          </ul>
        </details>
      )}
      <details className="legacy-assessments">
        <summary>Additional sensor-rule checks</summary>
        <p className="evidence-note">
          Current-condition rules. These checks do not confirm events or predict
          hazards six hours ahead.
        </p>
        {Object.values(t.risks || {}).map((r) => (
          <article className="risk-card" key={r.target}>
            <h4>{r.display_name}</h4>
            <strong>
              {r.abstain
                ? "Insufficient evidence"
                : r.level.replaceAll("_", " ")}
            </strong>
            <p>Rule score: {fmt(r.score)} / 1 · Calibration: unavailable</p>
            <details>
              <summary>Rule evidence</summary>
              <ul>
                {r.evidence.map((e) => (
                  <li key={e.feature}>
                    {e.feature}:{" "}
                    {e.value == null ? "Unavailable" : String(e.value)} {e.unit}{" "}
                    ·{" "}
                    {e.matched == null
                      ? "unknown"
                      : e.matched
                        ? "matched"
                        : "not matched"}
                  </li>
                ))}
              </ul>
            </details>
          </article>
        ))}
        <p className="evidence-note">
          Storm sequence:{" "}
          {t.stormSequence?.matched == null
            ? "Unavailable"
            : t.stormSequence.matched
              ? "Sequence matched"
              : "Not matched"}
          . Flash flood and landslide predictors are unavailable. Public alerts
          are disabled.
        </p>
      </details>
      {rpcAvailable ? (
        <button className="secondary-button" onClick={onOpenRpc}>
          Device commands
        </button>
      ) : (
        <p className="evidence-note">Device controls are not connected.</p>
      )}
    </section>
  );
}
export default function TelemetryPanel({
  nodeName,
  telemetry: t,
  loading,
  cached,
}) {
  if (!nodeName)
    return (
      <section className="telemetry-panel telemetry-empty">
        <h2>Choose a location</h2>
        <p>Readings and weather patterns will appear here.</p>
      </section>
    );
  return (
    <section className="telemetry-panel" aria-label="Location conditions">
      <div className="location-heading">
        <span className="eyebrow">Selected location</span>
        <h2>{nodeName}</h2>
        <p>{t ? readingTime(t.timestamp) : "Loading latest reading…"}</p>
      </div>
      {loading && <p className="loading-state">Updating readings…</p>}
      {!loading && !t && (
        <p className="empty-message">
          We couldn’t load this location. Please try again.
        </p>
      )}
      {!loading && t && (
        <>
          <div className="source-banner">
            <span className="source-label">{sourceName(t.sourceClass)}</span>
            {(cached || t.stale) && (
              <span className="stale-notice">
                {cached ? "Saved reading" : "Older reading"}
              </span>
            )}
          </div>
          <div className="sensor-grid">
            {Object.entries(CHANNELS).map(([key, [name, unit]]) => (
              <div className="sensor-cell" key={key}>
                <span className="sensor-label">{name}</span>
                <div className="sensor-value">
                  {fmt(t.sensors?.[key])}
                  <span className="sensor-unit"> {unit}</span>
                </div>
                <History rows={t.history || []} channel={key} />
              </div>
            ))}
          </div>
          <section className="forecast-section">
            <div className="section-heading">
              <h3>Six hours ahead</h3>
              <span className="section-tag">Estimate</span>
            </div>
            <p className="forecast-time">{readingTime(t.forecastTimestamp)}</p>
            {t.forecastStatus === "WARMING_UP_PERSISTENCE" && (
              <p className="reading-note">
                Building history. These estimates currently repeat the latest
                readings.
              </p>
            )}
            <div className="forecast-list">
              {Object.entries(CHANNELS).map(([key, [name, unit]]) => (
                <div key={key}>
                  <span>{name}</span>
                  <strong>
                    {fmt(t.forecast6h?.[key])}
                    <small> {unit}</small>
                  </strong>
                </div>
              ))}
            </div>
          </section>
          <WeatherCategories classification={t.weatherCategories} />
          <HazardScenarios assessment={t.hazardScenarios} />
        </>
      )}
    </section>
  );
}
