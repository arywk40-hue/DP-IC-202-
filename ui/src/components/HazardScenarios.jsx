import React from "react";
import { readingTime } from "../api/presentation";

const percent = (v) => `${(100 * v).toFixed(1)}%`;

export default function HazardScenarios({ assessment: a }) {
  const ready = a?.status === "SYNTHETIC_SCENARIOS_ONLY";
  return (
    <section className="weather-categories hazard-scenarios" aria-label="Hazard scenarios">
      <div className="section-heading">
        <h3>Himalayan hazard scenarios</h3>
        <span className="section-tag">Six-hour simulated outcomes</span>
      </div>
      <p className="pattern-source-note">
        These percentages are conditional fractions from simulated rainfall,
        soil and catchment assumptions. They are not calibrated probabilities
        of real events or operational warnings.
      </p>
      {ready ? a.targets.map((target) => (
        <div className="category-row" key={target.id} data-testid={`scenario-${target.id}`}>
          <span>
            {target.name}
            <small>{percent(target.scenario_fraction)} of simulated outcomes under central assumptions · assumption sensitivity: {percent(target.assumption_range[0])}–{percent(target.assumption_range[1])}</small>
            <span className="scenario-cases">
              {Object.entries(target.assumption_cases || {}).map(([key, item]) => (
                <span key={key}>{item.label}: <strong>{percent(item.scenario_fraction)} of simulated outcomes</strong></span>
              ))}
            </span>
          </span>
          <span className="category-score">{percent(target.scenario_fraction)}<small>Central simulated outcome fraction</small></span>
        </div>
      )) : <p className="reading-note">{a?.reason || "Six complete hourly readings are needed."}</p>}
      {ready && <p className="pattern-source-note">
        Source input: {a.source_class} · {a.source_id} · cell {a.source_cell_id} at {a.coordinates?.join(", ")}.
        <br />Observation {readingTime(a.observation_timestamp)}; assessed {readingTime(a.assessed_at_utc)}; six-hour endpoint {readingTime(a.forecast_timestamp)}.
        <br />Model {a.model_id} · config {a.config_sha256?.slice(0, 12)}… · code {a.implementation_sha256?.slice(0, 12)}… · seed {a.seed} · {a.draws_per_family} simulations per assumption family.
        <br />Pressure source: {a.pressure_reference}. Field validated: no. Calibrated: no. Public alerts: disabled.
      </p>}
      <details className="hazard-explanation">
        <summary>How are these calculated?</summary>
        <p>Past six-channel readings condition synthetic half-hour rainfall paths. PM2.5 and PM10 are retained in the model input contract but do not drive this rainfall generator.
          Monte Carlo runs then vary assumed soil wetness, drainage capacity,
          catchment size and slope susceptibility.</p>
        <p>Cloudburst is a simulated one-hour rainfall threshold exceedance.
          Flash flood is a simplified runoff-capacity scenario. Landslide is a
          transferred rainfall-trigger scenario on assumed susceptible terrain.</p>
        <p>Actual rainfall, soil, river flow and slope stability are not measured
          by these six channels. The range compares assumptions; it is not a
          confidence interval. No public alerts are issued.</p>
        {ready && <p>Unknown drivers for this run: {a.unknown_drivers?.join(", ") || "not listed"}. Field validated: false; calibrated: false; public alerts: disabled.</p>}
        {a?.research_sources?.length > 0 && <>
          <h4>Research used</h4>
          <ul>{a.research_sources.map((source) => <li key={source.id}>
            <a href={source.url} target="_blank" rel="noreferrer">{source.title || source.id}</a>: {source.supports}
          </li>)}</ul>
        </>}
        {a?.parameter_provenance && <details className="parameter-provenance">
          <summary>Parameter and prior provenance</summary>
          <p>{a.parameter_provenance.scope}</p>
          {Object.entries(a.parameter_provenance).filter(([key]) => key !== "scope").map(([section, values]) => <section key={section}>
            <h4>{section.replaceAll("_", " ")}</h4>
            <ul>{Object.entries(values).map(([key, value]) => <li key={key}>
              <code>{key}</code>: {typeof value === "string" ? value : [value.kind, value.role, value.evidence, value.limitation, value.source_id].filter(Boolean).join(" · ") || JSON.stringify(value)}
            </li>)}</ul>
          </section>)}
        </details>}
      </details>
    </section>
  );
}
