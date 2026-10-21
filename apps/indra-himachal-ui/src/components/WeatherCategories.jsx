import React from "react";
const names = {
  heatwave_like: "Heat stress",
  cloudburst_like: "Cloudburst-like pattern",
  wildfire_weather: "Hot, dry & windy",
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
    <div
      className={`category-row ${value.matched ? "category-match" : ""}`}
      data-testid={`category-${value.id}`}
    >
      <span>
        {names[value.id] || value.name}
        <small>{value.matched ? "Pattern matched" : "Not matched"}</small>
      </span>
      <span className="category-score">
        {value.score.toFixed(2)}
        <span className="category-bar">
          <i style={{ width: `${value.score * 100}%` }} />
        </span>
      </span>
    </div>
  );
}
export default function WeatherCategories({ classification: c }) {
  const ready = c?.status === "SYNTHETIC_PATTERN_SCORES_ONLY";
  const matched = c?.categories?.filter((v) => v.matched) || [];
  const other = c?.categories?.filter((v) => !v.matched) || [];
  return (
    <section className="weather-categories" aria-label="Weather patterns">
      <div className="section-heading">
        <h3>Weather patterns</h3>
        <span className="section-tag">Current reading</span>
      </div>
      {ready ? (
        <>
          <p className="pattern-summary">
            {matched.length
              ? `${matched.length === 1 ? "One pattern matches" : `${matched.length} patterns match`} these readings.`
              : "No trained extreme pattern matched."}
          </p>
          {matched.map((v) => (
            <Category key={v.id} value={v} />
          ))}
          <details className="other-patterns">
            <summary>
              {matched.length ? "Other patterns" : "View pattern scores"}{" "}
              <span>{other.length}</span>
            </summary>
            {other.map((v) => (
              <Category key={v.id} value={v} />
            ))}
          </details>
        </>
      ) : (
        <div className="quiet-empty">
          <strong>
            {c?.status === "OUTSIDE_SYNTHETIC_DOMAIN"
              ? "Outside the model’s range"
              : "More history needed"}
          </strong>
          <p>
            {c?.status === "OUTSIDE_SYNTHETIC_DOMAIN"
              ? "These readings fall outside the conditions covered during training."
              : "Six complete hours of readings are needed to assess patterns."}
          </p>
        </div>
      )}
      <p className="pattern-source-note">
        Pattern model trained on simulated scenarios.
      </p>
      <details className="score-explanation">
        <summary>What do these scores mean?</summary>
        <p>
          The model was trained on simulated sensor scenarios. Scores measure
          pattern matches, not real-event probabilities. Several patterns may
          match together. No match does not establish safe conditions.
        </p>
        <p>
          A cloudburst-like pattern does not confirm rainfall intensity. Heat
          stress is an instantaneous temperature pattern, not a sustained
          heatwave.
        </p>
      </details>
    </section>
  );
}
