import React from "react";
import { PARAMETERS, parameterColor } from "../api/parameter-colors";

export default function ParameterMaps({ data, selected, onSelect, cached }) {
  return (
    <section className="parameter-maps" aria-label="Parameter maps">
      <div className="section-heading">
        <h2>Parameter maps</h2>
        <span className="section-tag">
          {data?.nodes?.length || 0} locations
        </span>
      </div>
      <p>Choose a measurement to explore how it varies between locations.</p>
      {cached && (
        <p className="lab-warning">
          Showing saved maps. Reconnect for the latest readings.
        </p>
      )}
      <p className="map-context">
        {data?.layers && Object.keys(data.layers).length
          ? "Values between locations are estimated from their readings."
          : "An area map needs at least three locations with readings at the same time."}
      </p>
      <div className="parameter-grid">
        {Object.entries(PARAMETERS).map(([key, [name, unit]]) => {
          const layer = data?.layers?.[key],
            values = layer?.values;
          const rows = values?.length || 1,
            cols = values?.[0]?.length || 1;
          return (
            <button
              key={key}
              type="button"
              className={`parameter-card ${key === selected ? "parameter-selected" : ""}`}
              aria-pressed={key === selected}
              onClick={() => onSelect(key)}
              aria-label={`Show ${name} heatmap`}
            >
              <span className="parameter-card-title">
                {name} <small>{unit}</small>
              </span>
              {layer?.supported_cells > 0 ? (
                <svg
                  viewBox="0 0 120 70"
                  role="img"
                  aria-label={`${name} interpolated heatmap`}
                >
                  <rect width="120" height="70" fill="#edf1eb" />
                  {values.flatMap((row, i) =>
                    row.map((v, j) =>
                      v == null ? null : (
                        <rect
                          key={`${i}:${j}`}
                          x={(j * 120) / cols}
                          y={((rows - 1 - i) * 70) / rows}
                          width={120 / cols + 0.05}
                          height={70 / rows + 0.05}
                          fill={parameterColor(
                            layer.maximum > layer.minimum
                              ? (v - layer.minimum) /
                                  (layer.maximum - layer.minimum)
                              : 0.5,
                          )}
                        >
                          <title>
                            {v.toFixed(2)} {unit}
                          </title>
                        </rect>
                      ),
                    ),
                  )}
                  {data.geometry !== "SEGMENT" &&
                    data.bounds &&
                    data.nodes.map((n) => (
                      <circle
                        key={n.id}
                        cx={
                          ((n.lng - data.bounds[1]) /
                            (data.bounds[3] - data.bounds[1])) *
                          120
                        }
                        cy={
                          70 -
                          ((n.lat - data.bounds[0]) /
                            (data.bounds[2] - data.bounds[0])) *
                            70
                        }
                        r="2"
                        fill="white"
                        stroke="#101a2b"
                        strokeWidth=".8"
                      />
                    ))}
                </svg>
              ) : (
                <div className="parameter-empty">More locations needed</div>
              )}
              <span className="parameter-range">
                {Number.isFinite(layer?.minimum)
                  ? `${layer.minimum.toFixed(1)} → ${layer.maximum.toFixed(1)} ${unit}`
                  : "No area estimate yet"}
              </span>
              <small>
                {layer
                  ? `${layer.node_count} locations · ${layer.supported_cells} map cells`
                  : "Readings are available on the map"}
              </small>
            </button>
          );
        })}
      </div>
      <details className="map-method">
        <summary>About these maps</summary>
        <p>
          Colors show the local value range, not severity. White dots mark the
          supplied locations. Estimates use IDW inside their supported geometry,
          with no terrain correction. Two points support a line only.{" "}
          {data?.reason}
        </p>
      </details>
    </section>
  );
}
