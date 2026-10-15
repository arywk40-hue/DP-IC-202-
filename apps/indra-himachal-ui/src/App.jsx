import React, { useEffect, useState, useCallback } from 'react';
import StatusHeader from './components/StatusHeader';
import NodeList from './components/NodeList';
import MapView from './components/MapView';
import TelemetryPanel from './components/TelemetryPanel';
import RpcMenu from './components/RpcMenu';
import { getNodes, getStatus, getHeatmap, getTelemetry } from './api/client';
import { withCache } from './api/cache';
import { DASHBOARD_API_VERSION } from './api/contract';

// Polling intervals — chosen to stay well under the Master Node's
// 10 req/s stress-test ceiling (see report §3.4).
const NODES_POLL_MS = 8000;
const HEATMAP_POLL_MS = 60000;

export default function App() {
  const [nodes, setNodes] = useState([]);
  const [status, setStatus] = useState(null);
  const [heatmap, setHeatmap] = useState({ points: [], status: 'NOT_AVAILABLE' });
  const [isLive, setIsLive] = useState(false);
  const [cachedAt, setCachedAt] = useState(null);
  const [versionMismatch, setVersionMismatch] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [rpcTargetId, setRpcTargetId] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [error, setError] = useState(null);
  const [telemetryCached, setTelemetryCached] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);

  const refreshCore = useCallback(async () => {
    // Stagger status after nodes so we do not burst the Master's 10 req/s ceiling.
    const nodesRes = await withCache('nodes', getNodes);
    setNodes(nodesRes.value);
    setSelectedId((current) => current ?? nodesRes.value?.[0]?.id ?? null);
    await new Promise((r) => setTimeout(r, 400));
    const statusRes = await withCache('status', getStatus);
    setStatus(statusRes.value);
    if (statusRes.value?.appVersion && statusRes.value.appVersion !== DASHBOARD_API_VERSION) {
      setVersionMismatch(true);
    } else {
      setVersionMismatch(false);
    }
    const live = nodesRes.isLive && statusRes.isLive;
    setIsLive(live);
    const stamp = [nodesRes.cachedAt, statusRes.cachedAt].filter(Boolean);
    setCachedAt(live ? null : (stamp.length ? Math.min(...stamp) : null));
  }, []);

  const refreshHeatmap = useCallback(async () => {
    const res = await withCache('heatmap', getHeatmap);
    setHeatmap(res.value);
  }, []);

  useEffect(() => {
    let coreBusy = false;
    let mapBusy = false;
    const core = async () => {
      if (coreBusy) return;
      coreBusy = true;
      try { await refreshCore(); setError(null); setRefreshTick(v => v+1); }
      catch (e) { setError(e.message); setIsLive(false); }
      finally { coreBusy = false; }
    };
    const map = async () => {
      if (mapBusy) return;
      mapBusy = true;
      try { await refreshHeatmap(); } catch { setHeatmap({ points: [], status: 'UNAVAILABLE' }); }
      finally { mapBusy = false; }
    };
    core(); map();
    const coreTimer = setInterval(core, NODES_POLL_MS);
    const heatTimer = setInterval(map, HEATMAP_POLL_MS);
    return () => {
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
    setTelemetry(null);
    setTelemetryLoading(true);
    withCache(`telemetry:${selectedId}`, () => getTelemetry(selectedId)).then((res) => {
      if (!cancelled) {
        setTelemetry(res.value);
        setTelemetryCached(!res.isLive);
        setTelemetryLoading(false);
      }
    }).catch(e => { if (!cancelled) { setTelemetryLoading(false); setError(e.message); } });
    return () => {
      cancelled = true;
    };
  }, [selectedId, refreshTick]);

  const selectedNode = nodes.find((n) => n.id === selectedId);
  const rpcTargetNode = nodes.find((n) => n.id === rpcTargetId);

  return (
    <div className="app-shell">
      <StatusHeader
        status={status}
        isLive={isLive}
        cachedAt={cachedAt}
        nodeCount={nodes.length}
        versionMismatch={versionMismatch}
        showHeatmap={showHeatmap}
        onToggleHeatmap={() => setShowHeatmap((v) => !v)}
      />

      <div className="research-banner">
        {status?.syntheticDemo ? 'SYNTHETIC DEMO — not observed Mandi weather. ' : 'Research prototype. '}
        Six-hour numerical forecasts · Experimental current-condition risk scores · No calibrated hazard probabilities or public alerts.
        {status?.staleNodes > 0 && ` ${status.staleNodes} node(s) have stale observations.`}
      </div>
      {error && <div className="version-banner" role="alert">Connection/data unavailable. {error}</div>}
      <div className="app-body">
        <NodeList
          nodes={nodes}
          selectedId={selectedId}
          onSelect={handleSelect}
          onOpenRpc={setRpcTargetId}
        />

        <MapView
          nodes={nodes}
          heatmap={heatmap.points}
          heatmapStatus={heatmap.status}
          heatmapReason={heatmap.reason}
          selectedId={selectedId}
          showHeatmap={showHeatmap}
          onSelect={handleSelect}
          onOpenRpc={setRpcTargetId}
        />

        <TelemetryPanel
          nodeName={selectedNode?.name}
          telemetry={telemetry}
          loading={telemetryLoading}
          cached={telemetryCached}
          rpcAvailable={status?.rpcAvailable === true}
          onOpenRpc={selectedId ? () => setRpcTargetId(selectedId) : undefined}
        />
      </div>

      {rpcTargetId && (
        <RpcMenu
          nodeId={rpcTargetId}
          nodeName={rpcTargetNode?.name ?? rpcTargetId}
          onClose={() => setRpcTargetId(null)}
          available={status?.rpcAvailable === true}
        />
      )}
    </div>
  );
}
