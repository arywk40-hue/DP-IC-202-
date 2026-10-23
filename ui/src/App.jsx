import React, { useEffect, useState, useCallback, useRef } from "react";
import StatusHeader from "./components/StatusHeader";
import NodeList from "./components/NodeList";
import MapView from "./components/MapView";
import TelemetryPanel, { TechnicalDetails } from "./components/TelemetryPanel";
import RpcMenu from "./components/RpcMenu";
import StormRiskPanel from "./components/StormRiskPanel";
import ProvenancePanel from "./components/ProvenancePanel";
import ModelLab from "./components/ModelLab";
import ParameterMaps from "./components/ParameterMaps";
import {
  getNodes,
  getStatus,
  getHeatmap,
  getTelemetry,
  getAllParameterMaps,
} from "./api/client";
import { withCache } from "./api/cache";
import { DASHBOARD_API_VERSION } from "./api/contract";
import { locationName, sourceName, readingTime } from "./api/presentation";

// Polling intervals — chosen to stay well under the Master Node's
// 10 req/s stress-test ceiling (see report §3.4).
const NODES_POLL_MS = 8000;
const HEATMAP_POLL_MS = 60000;

export default function App() {
  const [view, setView] = useState("observations");
  const [nodes, setNodes] = useState([]);
  const telemetryIdentity = useRef(null);
  const [status, setStatus] = useState(null);
  const [heatmap, setHeatmap] = useState({
    points: [],
    status: "NOT_AVAILABLE",
  });
  const [parameter, setParameter] = useState("temperature_c");
  const [parameterMaps, setParameterMaps] = useState(null);
  const [mapsCached, setMapsCached] = useState(false);
  const mapRequest = useRef(0);
  const [isLive, setIsLive] = useState(false);
  const [cachedAt, setCachedAt] = useState(null);
  const [versionMismatch, setVersionMismatch] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [rpcTargetId, setRpcTargetId] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [error, setError] = useState(null);
  const [telemetryCached, setTelemetryCached] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  const refreshCore = useCallback(async () => {
    // Stagger status after nodes so we do not burst the Master's 10 req/s ceiling.
    const nodesRes = await withCache("nodes", getNodes);
    setNodes(nodesRes.value);
    setSelectedId((current) =>
      nodesRes.value?.some((node) => node.id === current)
        ? current
        : (nodesRes.value?.[0]?.id ?? null),
    );
    await new Promise((r) => setTimeout(r, 400));
    const statusRes = await withCache("status", getStatus);
    setStatus(statusRes.value);
    if (
      statusRes.value?.appVersion &&
      statusRes.value.appVersion !== DASHBOARD_API_VERSION
    ) {
      setVersionMismatch(true);
    } else {
      setVersionMismatch(false);
    }
    const live = nodesRes.isLive && statusRes.isLive;
    setIsLive(live);
    const stamp = [nodesRes.cachedAt, statusRes.cachedAt].filter(Boolean);
    setCachedAt(live ? null : stamp.length ? Math.min(...stamp) : null);
  }, []);

  const refreshHeatmap = useCallback(async () => {
    const generation = ++mapRequest.current;
    const res = await withCache(`heatmap:${parameter}`, () =>
      getHeatmap(parameter),
    );
    const all = await withCache("parameter-maps", getAllParameterMaps);
    if (generation !== mapRequest.current) return;
    setHeatmap(res.value);
    setParameterMaps(all.value);
    setMapsCached(!res.isLive || !all.isLive);
  }, [parameter]);

  useEffect(() => {
    let coreBusy = false;
    let mapBusy = false;
    const core = async () => {
      if (coreBusy) return;
      coreBusy = true;
      try {
        await refreshCore();
        setError(null);
        setRefreshTick((v) => v + 1);
      } catch (e) {
        setError(e.message);
        setIsLive(false);
      } finally {
        coreBusy = false;
      }
    };
    const map = async () => {
      if (mapBusy) return;
      mapBusy = true;
      try {
        await refreshHeatmap();
      } catch {
        setHeatmap({ points: [], status: "UNAVAILABLE" });
        setMapsCached(true);
      } finally {
        mapBusy = false;
      }
    };
    core();
    map();
    const coreTimer = setInterval(core, NODES_POLL_MS);
    const heatTimer = setInterval(map, HEATMAP_POLL_MS);
    return () => {
      mapRequest.current++;
      clearInterval(coreTimer);
      clearInterval(heatTimer);
    };
  }, [refreshCore, refreshHeatmap]);

  const handleSelect = useCallback((id) => {
    setSelectedId(id);
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTelemetry(null);
      return;
    }
    let cancelled = false;
    if (telemetryIdentity.current !== selectedId) {
      setTelemetry(null);
      setTelemetryLoading(true);
    }
    telemetryIdentity.current = selectedId;
    withCache(`telemetry:${selectedId}`, () => getTelemetry(selectedId))
      .then((res) => {
        if (!cancelled) {
          setTelemetry(res.value);
          setTelemetryCached(!res.isLive);
          setTelemetryLoading(false);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setTelemetryLoading(false);
          setError(e.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId, refreshTick]);

  const selectedNode = nodes.find((n) => n.id === selectedId);
  const rpcTargetNode = nodes.find((n) => n.id === rpcTargetId);

  const latest = nodes.length
    ? Math.max(...nodes.map((n) => n.lastSeen))
    : null;
  const source =
    status?.syntheticDemo ||
    nodes.some((n) => n.sourceClass === "synthetic_demo")
      ? "synthetic_demo"
      : status?.sourceClasses?.includes("modeled_grid") ||
          nodes.some((n) => n.sourceClass === "modeled_grid")
        ? "modeled_grid"
        : status?.sourceClasses?.[0] || nodes[0]?.sourceClass;
  const selectParameter = (key) => {
    setParameter(key);
    setShowHeatmap(true);
    setView("observations");
  };
  return (
    <div className="app-shell">
      <StatusHeader
        isLive={isLive}
        cachedAt={cachedAt}
        versionMismatch={versionMismatch}
        view={view}
        onViewChange={setView}
      />
      <main className="main-content">
        <div className="workspace-heading">
          <div>
            <span className="eyebrow">Your weather network</span>
            <h1>
              {view === "observations"
                ? "Across your locations"
                : view === "parameters"
                  ? "Explore the area"
                  : "Data & system"}
            </h1>
          </div>
          <div className="workspace-meta">
            <span className="source-chip">{sourceName(source)}</span>
            <span>{latest ? readingTime(latest) : "Waiting for readings"}</span>
          </div>
        </div>
        <div className="data-context" role="note">
          {source === "synthetic_demo"
            ? "These are simulated readings, not measurements from actual stations."
            : source === "modeled_grid"
              ? "Showing weather-model estimates, not sensor measurements."
              : "Location readings and estimates are shown with their observation times."}
        </div>
        {error && (
          <div className="version-banner" role="alert">
            Unable to refresh. Your last saved readings may still be available.
          </div>
        )}
        {view === "observations" && (
          <div className="app-body">
            <NodeList
              nodes={nodes}
              selectedId={selectedId}
              onSelect={handleSelect}
            />
            <MapView
              nodes={nodes}
              heatmap={heatmap.channel === parameter ? heatmap : null}
              heatmapStatus={heatmap.status}
              heatmapReason={heatmap.reason}
              selectedId={selectedId}
              showHeatmap={showHeatmap}
              parameter={parameter}
              onParameterChange={(key) => {
                setParameter(key);
                setShowHeatmap(true);
              }}
              onToggleHeatmap={() => setShowHeatmap((v) => !v)}
              onSelect={handleSelect}
            />
            <TelemetryPanel
              nodeName={selectedNode ? locationName(selectedNode) : null}
              telemetry={telemetry}
              loading={telemetryLoading}
              cached={telemetryCached}
            />
          </div>
        )}
        {view === "parameters" && (
          <ParameterMaps
            data={parameterMaps}
            selected={parameter}
            cached={Boolean(parameterMaps) && (mapsCached || !isLive)}
            onSelect={selectParameter}
          />
        )}
        {view === "system" && (
          <div className="system-view">
            <section className="system-intro">
              <h2>Behind the readings</h2>
              <p>Data sources, model performance and device information.</p>
              <label className="system-location">
                Location
                <select
                  value={selectedId || ""}
                  onChange={(e) => handleSelect(e.target.value)}
                >
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {locationName(n)}
                    </option>
                  ))}
                </select>
              </label>
            </section>
            <TechnicalDetails
              telemetry={telemetry}
              rpcAvailable={status?.rpcAvailable === true}
              onOpenRpc={() => setRpcTargetId(selectedId)}
            />
            <ProvenancePanel />
            <ModelLab />
            <StormRiskPanel />
          </div>
        )}
        <footer className="app-footer">
          <span>
            INDRA <span className="footer-separator">/</span> Local weather, in
            context.
          </span>
          <button onClick={() => setView("system")}>
            Data & model information <span aria-hidden="true">↗</span>
          </button>
        </footer>
      </main>
      {rpcTargetId && (
        <RpcMenu
          nodeId={rpcTargetId}
          nodeName={locationName(rpcTargetNode)}
          onClose={() => setRpcTargetId(null)}
          available={status?.rpcAvailable === true}
        />
      )}
    </div>
  );
}
