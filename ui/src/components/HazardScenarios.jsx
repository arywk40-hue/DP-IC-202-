import React from "react";

const percent = (v) => `${(100 * v).toFixed(1)}%`;

export default function HazardScenarios({ assessment: a }) {
  const ready = a?.status === "SYNTHETIC_SCENARIOS_ONLY";
  return (
    <section className="weather-categories hazard-scenarios" aria-label="Hazard scenarios">
      <div className="section-heading">
        <h3>Hazard scenarios</h3>
        <span className="section-tag">Next six hours · simulated</span>
      </div>
      <p className="pattern-source-note">
        Simulated outcomes under assumed rainfall and ground conditions. These
        percentages are not the chance of a real event.
      </p>
      {ready ? a.targets.map((t) => (
        <div className="category-row" key={t.id} data-testid={`scenario-${t.id}`}>
          <span>{t.name}<small>Across assumptions: {t.assumption_range.map(percent).join(" – ")}</small></span>
          <span className="category-score">{percent(t.scenario_fraction)}<small>Central case</small></span>
        </div>
      )) : <p className="reading-note">{a?.reason || "Six complete hours of readings are needed."}</p>}
      <details className="hazard-explanation">
        <summary>How are these calculated?</summary>
        <p>Each reading is tested against simulated six-hour rainfall paths, soil
          wetness and drainage capacity. The central case is one assumed setting;
          the range compares drier and wetter settings, not a confidence interval.</p>
        <p>Cloudburst means the simulated one-hour rainfall crosses 100 mm. Flood
          means simplified runoff exceeds an assumed channel capacity. Landslide
          means a transferred rainfall threshold is exceeded on assumed susceptible
          terrain; it does not model an actual slope failure.</p>
        <p>Rainfall, soil and catchment properties are not measured by these six
          channels. No alerts are sent from these estimates. Even 0% does not mean safe.</p>
      </details>
    </section>
  );
}
