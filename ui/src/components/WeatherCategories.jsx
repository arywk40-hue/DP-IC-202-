import React from "react";

const names = {
  heatwave_like: "Heat stress",
  cloudburst_like: "Cloudburst-like pattern",
  wildfire_weather: "Hot, dry and windy",
  rain: "Rain-like pattern",
  fog: "Fog-like pattern",
  frost: "Frost-like pattern",
  smoke: "Smoke / pollution pattern",
  snowstorm: "Snowstorm pattern",
  rainstorm: "Rainstorm pattern",
  dust_storm: "Dust storm pattern",
};

function Category({ value }) {
  return (
    <div className={`category-row ${value.matched ? "category-match" : ""}`} data-testid={`category-${value.id}`}>
      <span>{names[value.id] || value.name}<small>{value.matched ? "Pattern matched" : "Below pattern threshold"}</small></span>
      <span className="category-score">{value.score.toFixed(2)}<small>score · cutoff {value.threshold.toFixed(2)}</small><span className="category-bar"><i style={{ width: `${value.score * 100}%` }} /></span></span>
    </div>
  );
}

export default function WeatherCategories({ classification: c }) {
  const ready = c?.status === "SYNTHETIC_PATTERN_SCORES_ONLY";
  const matched = c?.categories?.filter((value) => value.matched) || [];
  const other = c?.categories?.filter((value) => !value.matched) || [];
  return (
    <section className="weather-categories" aria-label="Weather pattern scores">
      <div className="section-heading"><h3>Weather pattern scores</h3><span className="section-tag">Current conditions · experimental</span></div>
      {ready ? <>
        <p className="pattern-summary">{matched.length ? `${matched.length} sensor pattern${matched.length === 1 ? "" : "s"} matched.` : "No trained sensor pattern matched."}</p>
        {matched.map((value) => <Category key={value.id} value={value} />)}
        <details className="other-patterns">
          <summary>{matched.length ? "Other pattern scores" : "View pattern scores"} <span>{other.length}</span></summary>
          {other.map((value) => <Category key={value.id} value={value} />)}
        </details>
      </> : <div className="quiet-empty">
        <strong>{c?.status === "OUTSIDE_SYNTHETIC_DOMAIN" ? "Outside training range" : "More hourly history needed"}</strong>
        <p>{c?.missing_features?.length ? "The model needs seven consecutive complete hourly readings." : c?.summary || "Pattern scores are unavailable."}</p>
      </div>}
      <p className="pattern-source-note">Trained on synthetic sensor patterns; scores are not event probabilities.</p>
      <details className="score-explanation">
        <summary>What do these scores mean?</summary>
        <p>Scores indicate similarity to simulated sensor patterns. They are not calibrated probabilities that a real event is occurring. Several patterns can match, and no match does not establish safe conditions.</p>
        <p>Cloudburst-like and storm scores do not confirm rain intensity, thunderstorm, flooding or slope failure.</p>
        {ready && <p>Source {c.source_class} · {c.source_id} · cell {c.source_cell_id} at {c.coordinates?.join(", ")}. Observation {c.observation_timestamp}.</p>}
        {ready && <p>Model {c.model_id} · {c.feature_count} raw/derived features · trained on {Object.values(c.training_rows_by_role || {}).reduce((sum, count) => sum + count, 0).toLocaleString()} synthetic episodes · profile {c.profile_sha256?.slice(0, 12)}… · no real-event labels.</p>}
        {ready && <p>Cutoffs define matches to synthetic proxy categories; they are not decision thresholds for real hazards.</p>}
      </details>
    </section>
  );
}
