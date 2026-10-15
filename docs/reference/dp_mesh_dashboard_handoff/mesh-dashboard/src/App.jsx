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
  const [heatmap, setHeatmap] = useState([]);
  const [isLive, setIsLive] = useState(true);
  const [cachedAt, setCachedAt] = useState(null);
  const [versionMismatch, setVersionMismatch] = useState(false);

  const [selectedId, setSelectedId] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryLoading, setTelemetryLoading] = useState(false);
  const [rpcTargetId, setRpcTargetId] = useState(null);
  const [showHeatmap, setShowHeatmap] = useState(true);

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
    refreshCore();
    refreshHeatmap();
    const coreTimer = setInterval(refreshCore, NODES_POLL_MS);
    const heatTimer = setInterval(refreshHeatmap, HEATMAP_POLL_MS);
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
    setTelemetryLoading(true);
    withCache(`telemetry:${selectedId}`, () => getTelemetry(selectedId)).then((res) => {
      if (!cancelled) {
        setTelemetry(res.value);
        setTelemetryLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

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

      <div className="app-body">
        <NodeList
          nodes={nodes}
          selectedId={selectedId}
          onSelect={handleSelect}
          onOpenRpc={setRpcTargetId}
        />

        <MapView
          nodes={nodes}
          heatmap={heatmap}
          selectedId={selectedId}
          showHeatmap={showHeatmap}
          onSelect={handleSelect}
          onOpenRpc={setRpcTargetId}
        />

        <TelemetryPanel
          nodeName={selectedNode?.name}
          telemetry={telemetry}
          loading={telemetryLoading}
          onOpenRpc={selectedId ? () => setRpcTargetId(selectedId) : undefined}
        />
      </div>

      {rpcTargetId && (
        <RpcMenu
          nodeId={rpcTargetId}
          nodeName={rpcTargetNode?.name ?? rpcTargetId}
          onClose={() => setRpcTargetId(null)}
        />
      )}
    </div>
  );
}
