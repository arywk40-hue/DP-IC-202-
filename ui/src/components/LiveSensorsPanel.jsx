import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getSensorsCombined,
  getSensorHistory,
  getSensorHeatmap,
  postSensorReadings,
} from "../api/client";
import MapView from "./MapView";

// Physical ESP32 readings only. Every number on this page came from a board via
// POST /api/ingest; nothing here is modeled, simulated or filled in.
const POLL_MS = 5000;
const CHANNELS = [
  ["temperature_c", "Temperature", "°C", 1],
  ["relative_humidity_pct", "Humidity", "%", 0],
  ["pressure_hpa", "Pressure", "hPa", 1],
  ["pm25_ug_m3", "PM2.5", "µg/m³", 0],
  ["pm10_ug_m3", "PM10", "µg/m³", 0],
  ["wind_speed_mps", "Wind", "m/s", 1],
];
const STATUS_LABEL = {
  ONLINE: "Online",
  STALE: "Late",
  OFFLINE: "Offline",
  NO_DATA: "Registered, no data",
};

const fmt = (v, digits = 1) =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : Number(v).toFixed(digits);

function age(seconds) {
  if (seconds === null || seconds === undefined) return "never";
  if (seconds < 60) return `${Math.round(seconds)} s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h ago`;
  return `${Math.round(seconds / 86400)} d ago`;
}

function NetworkSummary({ view }) {
  const { network } = view;
  const spatial = network.spatial;
  return (
    <section className="live-card">
      <div className="live-card-head">
        <h3>Combined network</h3>
        <span className="live-muted">
          {network.contributing_nodes} node
          {network.contributing_nodes === 1 ? "" : "s"} contributing · quorum{" "}
          {network.quorum_needed || "—"} ({network.quorum_rule})
        </span>
      </div>
      <div className="live-channel-grid">
        {CHANNELS.map(([key, label, unit, digits]) => {
          const s = network.channels[key];
          return (
            <div key={key} className="live-channel">
              <span className="live-channel-label">{label}</span>
              <strong className="live-channel-value">
                {s ? fmt(s.mean, digits) : "—"}
                <small> {unit}</small>
              </strong>
              <span className="live-muted">
                {s
                  ? s.n > 1
                    ? `${fmt(s.min, digits)} – ${fmt(s.max, digits)} · spread ${fmt(s.spread, digits)}`
                    : "1 node"
                  : "no fresh reading"}
              </span>
            </div>
          );
        })}
      </div>
      <div className="live-spatial">
        <div>
          <span className="live-channel-label">Lapse rate</span>
          <strong>
            {spatial.lapse_rate_c_per_km === null
              ? "—"
              : `${fmt(spatial.lapse_rate_c_per_km, 2)} °C/km`}
          </strong>
        </div>
        <div>
          <span className="live-channel-label">Pressure gradient</span>
          <strong>
            {spatial.pressure_gradient_hpa_per_km === null
              ? "—"
              : `${fmt(spatial.pressure_gradient_hpa_per_km, 1)} hPa/km`}
          </strong>
        </div>
        <div>
          <span className="live-channel-label">Wind shear</span>
          <strong>
            {spatial.wind_shear_mps === null ? "—" : `${fmt(spatial.wind_shear_mps, 1)} m/s`}
          </strong>
        </div>
        <div>
          <span className="live-channel-label">Stability</span>
          <strong>{spatial.stability ? spatial.stability.replaceAll("_", " ").toLowerCase() : "—"}</strong>
        </div>
      </div>
      {spatial.note && <p className="live-muted live-note">{spatial.note}</p>}
    </section>
  );
}

function ForecastLine({ forecast }) {
  if (!forecast) return null;
  if (forecast.status === "HYBRID_READY") {
    const v = forecast.values;
    return (
      <p className="live-forecast">
        <strong>+6 h:</strong> {fmt(v.temperature_c)} °C · {fmt(v.relative_humidity_pct, 0)}% ·{" "}
        {fmt(v.pressure_hpa)} hPa · PM2.5 {fmt(v.pm25_ug_m3, 0)} · wind {fmt(v.wind_speed_mps)} m/s
      </p>
    );
  }
  if (forecast.status === "WARMING_UP_PERSISTENCE" || forecast.status === "NO_DATA") {
    return (
      <p className="live-forecast live-muted">
        Forecast warming up: {forecast.history_hours ?? 0}/{forecast.required_hours ?? 25} complete
        hours of history.
      </p>
    );
  }
  return (
    <p className="live-forecast live-muted">
      Forecast unavailable ({forecast.status}
      {forecast.error ? `: ${forecast.error}` : ""})
    </p>
  );
}

function NodeCard({ node, selected, onSelect }) {
  const r = node.reading;
  return (
    <button
      type="button"
      className={`live-node ${selected ? "live-node-active" : ""}`}
      onClick={() => onSelect(node.node_id)}
      aria-pressed={selected}
    >
      <div className="live-node-head">
        <span className={`live-dot live-dot-${node.status.toLowerCase()}`} />
        <strong>{node.name}</strong>
        <span className="live-muted">{node.node_id !== node.name ? node.node_id : ""}</span>
      </div>
      <div className="live-node-meta live-muted">
        {STATUS_LABEL[node.status] || node.status} · {age(node.age_seconds)}
        {node.battery_v != null && ` · ${fmt(node.battery_v, 2)} V`}
        {node.elevation_m != null && ` · ${fmt(node.elevation_m, 0)} m`}
        {node.transport && ` · ${node.transport === "espnow" ? "radio via master" : node.transport.replace("_", " ")}`}
        {node.rssi_dbm != null && ` · ${fmt(node.rssi_dbm, 0)} dBm`}
      </div>
      {r ? (
        <div className="live-node-values">
          {CHANNELS.map(([key, label, unit, digits]) => (
            <span key={key}>
              <small>{label}</small>
              {fmt(r[key], digits)} <small>{unit}</small>
            </span>
          ))}
        </div>
      ) : (
        <p className="live-muted">Waiting for the first reading.</p>
      )}
      {r?.timestamp_source === "server_receive" && (
        <p className="live-muted live-note">No clock on board: time is when the server received it.</p>
      )}
      <ForecastLine forecast={node.forecast_6h} />
    </button>
  );
}

function HistoryChart({ nodeId }) {
  const [channel, setChannel] = useState("temperature_c");
  const [hours, setHours] = useState(6);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      getSensorHistory(nodeId, hours, 3000)
        .then((res) => !cancelled && (setData(res.readings), setError(null)))
        .catch((e) => !cancelled && setError(e.message));
    load();
    const t = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [nodeId, hours]);

  const meta = CHANNELS.find((c) => c[0] === channel);
  const points = useMemo(
    () =>
      (data || [])
        .filter((r) => r[channel] !== null && r[channel] !== undefined)
        .map((r) => [Date.parse(r.timestamp_utc), r[channel]]),
    [data, channel],
  );
  const W = 1000, H = 220, P = 36;
  let path = "", minV = 0, maxV = 0, t0 = 0, t1 = 0;
  if (points.length > 1) {
    t0 = points[0][0]; t1 = points[points.length - 1][0];
    minV = Math.min(...points.map((p) => p[1]));
    maxV = Math.max(...points.map((p) => p[1]));
    const pad = (maxV - minV || 1) * 0.1;
    minV -= pad; maxV += pad;
    const x = (t) => P + ((t - t0) / (t1 - t0 || 1)) * (W - 2 * P);
    const y = (v) => H - P + 8 - ((v - minV) / (maxV - minV)) * (H - 2 * P);
    path = points.map((p, i) => `${i ? "L" : "M"}${x(p[0]).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  }
  const clock = (t) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <section className="live-card">
      <div className="live-card-head">
        <h3>History · {nodeId}</h3>
        <div className="live-controls">
          <select value={channel} onChange={(e) => setChannel(e.target.value)} aria-label="Channel">
            {CHANNELS.map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
          <select value={hours} onChange={(e) => setHours(Number(e.target.value))} aria-label="Window">
            {[1, 6, 24, 72].map((h) => (
              <option key={h} value={h}>Last {h} h</option>
            ))}
          </select>
        </div>
      </div>
      {error && <p className="live-error">{error}</p>}
      {points.length > 1 ? (
        <svg viewBox={`0 0 ${W} ${H}`} className="live-chart" role="img"
             aria-label={`${meta[1]} over the last ${hours} hours`}>
          <line x1={P} x2={W - P} y1={H - P + 8} y2={H - P + 8} className="live-axis" />
          <text x={P} y={14} className="live-axis-label">{fmt(maxV, meta[3])} {meta[2]}</text>
          <text x={P} y={H - P - 2} className="live-axis-label">{fmt(minV, meta[3])}</text>
          <text x={P} y={H - 4} className="live-axis-label">{clock(t0)}</text>
          <text x={W - P} y={H - 4} textAnchor="end" className="live-axis-label">{clock(t1)}</text>
          <path d={path} className="live-line" />
        </svg>
      ) : (
        <p className="live-muted">Not enough {meta[1].toLowerCase()} readings in this window yet.</p>
      )}
    </section>
  );
}

const EXCLUDED_LABEL = {
  OLDER_THAN_SYNC_WINDOW: "reading older than the others",
  NO_LOCATION: "no location set",
  NO_VALUE_FOR_CHANNEL: "no reading for this measurement",
  DUPLICATE_LOCATION_OR_SOURCE_CELL: "same position as another node",
};

function SensorMap({ view, selected, onSelect }) {
  const [parameter, setParameter] = useState("temperature_c");
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [heatmap, setHeatmap] = useState(null);
  const [error, setError] = useState(null);
  const [area, setArea] = useState("auto"); // "auto" | km number as string | "between"
  const tick = view.generated_at_utc;

  useEffect(() => {
    let cancelled = false;
    const opts = area === "between" ? { mode: "hull", resolution: 24 }
      : { mode: "radius", radiusKm: area === "auto" ? null : Number(area) };
    getSensorHeatmap(parameter, opts)
      .then((res) => !cancelled && (setHeatmap(res), setError(null)))
      .catch((e) => !cancelled && setError(e.message));
    return () => { cancelled = true; };
  }, [parameter, tick, area]);

  const nodes = view.nodes
    .filter((n) => n.lat != null && n.lon != null)
    .map((n) => ({
      id: n.node_id,
      name: n.name,
      lat: n.lat,
      lng: n.lon,
      lastSeen: Date.now() - (n.age_seconds ?? 1e9) * 1000,
      reportingIntervalSeconds: 60,
      sourceClass: "physical_sensor",
      stale: n.status !== "ONLINE",
    }));

  return (
    <section className="live-card live-map">
      <div className="live-card-head">
        <h3>Map</h3>
        <div className="live-controls">
          <select value={area} onChange={(e) => setArea(e.target.value)} aria-label="Area covered">
            <option value="auto">
              Area: auto{heatmap?.mode === "radius" && heatmap?.radius_km && area === "auto"
                ? ` (${heatmap.radius_km < 1 ? `${Math.round(heatmap.radius_km * 1000)} m` : `${heatmap.radius_km} km`})` : ""}
            </option>
            {[0.25, 0.5, 1, 2, 5, 10, 25].map((k) => (
              <option key={k} value={String(k)}>
                Area: {k < 1 ? `${k * 1000} m` : `${k} km`} around nodes
              </option>
            ))}
            <option value="between">Only between nodes</option>
          </select>
        </div>
      </div>
      <p className="live-muted live-map-status">
        {heatmap?.mode === "radius" && heatmap?.features?.length
          ? `${heatmap.reason} Cells: ${heatmap.cell_size_km} km.`
          : heatmap?.status === "LINE_ESTIMATE"
            ? "Nodes lie along one line: colors are estimated along that transect only."
            : heatmap?.status === "AREA_ESTIMATE"
              ? "Colors are estimated only inside the area your nodes enclose."
              : heatmap?.reason || ""}
      </p>
      <MapView
        nodes={nodes}
        heatmap={heatmap && heatmap.channel === parameter ? heatmap : null}
        heatmapStatus={heatmap?.status}
        heatmapReason={heatmap?.reason}
        selectedId={selected}
        showHeatmap={showHeatmap}
        parameter={parameter}
        onParameterChange={(key) => { setParameter(key); setShowHeatmap(true); }}
        onToggleHeatmap={() => setShowHeatmap((v) => !v)}
        onSelect={onSelect}
        areaBounds={showHeatmap && heatmap?.mode === "radius" ? heatmap.bounds : null}
      />
      {error && <p className="live-error">{error}</p>}
      {heatmap?.elevation_note && <p className="live-muted live-note">{heatmap.elevation_note}</p>}
      {heatmap?.excluded_nodes?.length > 0 && (
        <p className="live-muted live-note">
          Not on the color map:{" "}
          {heatmap.excluded_nodes.map((e) => `${e.id} (${EXCLUDED_LABEL[e.reason] || e.reason})`).join(", ")}
        </p>
      )}
    </section>
  );
}

function UsbBridge({ onSent }) {
  const supported = typeof navigator !== "undefined" && "serial" in navigator;
  const [state, setState] = useState("idle");
  const [nodeId, setNodeId] = useState("");
  const [log, setLog] = useState([]);
  const portRef = useRef(null);
  const stopRef = useRef(false);

  const note = (line) => setLog((l) => [line, ...l].slice(0, 6));

  const connect = async () => {
    try {
      const port = await navigator.serial.requestPort();
      await port.open({ baudRate: 115200 });
      portRef.current = port;
      stopRef.current = false;
      setState("connected");
      note("Connected. Forwarding one reading every 5 s.");
      const reader = port.readable.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      let last = 0;
      while (!stopRef.current) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += value;
        const lines = buffer.split("\n");
        buffer = lines.pop();
        for (const raw of lines) {
          const line = raw.trim();
          if (!line.startsWith("{")) {
            if (line.startsWith("INDRA node") || line.startsWith("status")) note(line);
            continue;
          }
          if (Date.now() - last < 5000) continue;
          let payload;
          try { payload = JSON.parse(line); } catch { continue; }
          if (!Array.isArray(payload.observations)) continue;
          for (const o of payload.observations) {
            if (nodeId) o.node_id = nodeId;
            o.transport = "web_serial";
          }
          last = Date.now();
          postSensorReadings(payload)
            .then(() => { note(`Sent ${payload.observations[0].node_id} at ${new Date().toLocaleTimeString()}`); onSent(); })
            .catch((e) => note(`Rejected: ${e.message.slice(0, 160)}`));
        }
      }
      reader.releaseLock();
    } catch (e) {
      note(`Serial error: ${e.message}`);
    } finally {
      try { await portRef.current?.close(); } catch { /* already closed */ }
      setState("idle");
    }
  };

  return (
    <section className="live-card">
      <div className="live-card-head">
        <h3>Plug a board into this computer</h3>
        <span className="live-muted">Chrome or Edge · USB serial at 115200 baud</span>
      </div>
      {!supported ? (
        <p className="live-muted">
          This browser has no Web Serial. Use Chrome/Edge, or run{" "}
          <code>.venv/bin/python server/scripts/serial_bridge.py</code>.
        </p>
      ) : (
        <div className="live-controls">
          <input
            value={nodeId}
            onChange={(e) => setNodeId(e.target.value.replace(/[^A-Za-z0-9_-]/g, ""))}
            placeholder="Node id override (optional)"
            aria-label="Node id override"
            disabled={state !== "idle"}
          />
          {state === "idle" ? (
            <button type="button" className="live-button" onClick={connect}>Connect board</button>
          ) : (
            <button type="button" className="live-button" onClick={() => { stopRef.current = true; }}>
              Disconnect
            </button>
          )}
        </div>
      )}
      {log.length > 0 && (
        <ul className="live-log">
          {log.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      )}
    </section>
  );
}

function SetupHelp() {
  return (
    <section className="live-card">
      <h3>No sensor nodes yet</h3>
      <p className="live-muted">Readings appear here as soon as any board sends one. Three ways in:</p>
      <ol className="live-steps">
        <li>
          <strong>USB, from this page:</strong> use “Connect board” below (Chrome/Edge).
        </li>
        <li>
          <strong>USB, background:</strong>{" "}
          <code>.venv/bin/python server/scripts/serial_bridge.py --node-id ridge-01</code>
        </li>
        <li>
          <strong>WiFi:</strong> set SSID, password and server URL in{" "}
          <code>esp32/operational_node/include/device_config.h</code>; start the server with{" "}
          <code>--host 0.0.0.0</code>.
        </li>
      </ol>
      <p className="live-muted">Test without hardware:</p>
      <pre className="live-pre">{`curl -X POST http://127.0.0.1:8080/api/ingest -H 'Content-Type: application/json' \\
  -d '{"node_id":"test-01","temperature_c":21.4,"relative_humidity_pct":60,"pressure_hpa":1008}'`}</pre>
    </section>
  );
}

export default function LiveSensorsPanel() {
  const [view, setView] = useState(null);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const res = await getSensorsCombined(true);
      setView(res);
      setError(null);
      setSelected((cur) =>
        res.nodes.some((n) => n.node_id === cur) ? cur : res.nodes.find((n) => n.reading)?.node_id ?? null,
      );
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, [refresh]);

  return (
    <div className="live-sensors">
      <div className="reading-note" role="note">
        Physical sensor readings only, sent by your ESP32 boards. Not field-validated.
        {view && ` Updated ${new Date(view.generated_at_utc).toLocaleTimeString()}.`}
      </div>
      {error && <p className="live-error" role="alert">Cannot reach the sensor API: {error}</p>}
      {view && (
        <div className="live-summary">
          <span><span className="live-dot live-dot-online" /> {view.online} online</span>
          <span><span className="live-dot live-dot-stale" /> {view.stale} late</span>
          <span><span className="live-dot live-dot-offline" /> {view.offline} offline</span>
          <span className="live-muted">{view.node_count} node{view.node_count === 1 ? "" : "s"} total</span>
        </div>
      )}
      {view && view.node_count === 0 && <SetupHelp />}
      {view && view.node_count > 0 && (
        <>
          <NetworkSummary view={view} />
          <SensorMap view={view} selected={selected} onSelect={setSelected} />
          <div className="live-node-grid">
            {view.nodes.map((n) => (
              <NodeCard key={n.node_id} node={n} selected={n.node_id === selected} onSelect={setSelected} />
            ))}
          </div>
          {selected && <HistoryChart nodeId={selected} />}
        </>
      )}
      <UsbBridge onSent={refresh} />
    </div>
  );
}
