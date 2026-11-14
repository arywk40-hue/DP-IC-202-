import React, { useState } from 'react';

const INITIAL_NODES = [
  {
    id: 'indra-master-01',
    nodeId: 0,
    name: 'Mandi Catchment Gateway',
    role: 'MASTER_GATEWAY',
    roleLabel: 'Master Gateway (Node 0)',
    location: 'Catchment Base Station / Hydromet Center',
    lat: 31.7100,
    lon: 76.9300,
    elevationM: 760,
    terrain: 'Valley Floor Base Camp',
    firmware: 'esp32-s3-mandi-v2',
    batteryMv: 4200,
    linkRssi: 0,
    active: true,
    measurements: {
      temperature_c: 18.4,
      relative_humidity_pct: 78.0,
      pressure_hpa: 930.5,
      pm25_ug_m3: 28.0,
      pm10_ug_m3: 42.0,
      wind_speed_mps: 2.4,
    },
    flashCommand: 'python esp32/tools/flash_esp32.py --role master --node-id 0',
  },
  {
    id: 'indra-slave-01',
    nodeId: 1,
    name: 'Uphill Ridge Unit 1',
    role: 'SLAVE_SENSOR',
    roleLabel: 'Peripheral Slave (Node 1)',
    location: 'Upstream Mountain Ridge (Slope)',
    lat: 31.7250,
    lon: 76.9420,
    elevationM: 1280,
    terrain: 'Steep Orographic Ridge',
    firmware: 'operational_node',
    batteryMv: 3980,
    linkRssi: -66,
    active: true,
    measurements: {
      temperature_c: 14.8,
      relative_humidity_pct: 86.0,
      pressure_hpa: 873.2,
      pm25_ug_m3: 16.0,
      pm10_ug_m3: 24.0,
      wind_speed_mps: 6.8,
    },
    flashCommand: 'python esp32/tools/flash_esp32.py --role slave --node-id 1',
  },
  {
    id: 'indra-slave-02',
    nodeId: 2,
    name: 'Downvalley Riverbed Unit 2',
    role: 'SLAVE_SENSOR',
    roleLabel: 'Peripheral Slave (Node 2)',
    location: 'Downvalley Riverbed / Drainage Basin',
    lat: 31.6980,
    lon: 76.9180,
    elevationM: 710,
    terrain: 'Catchment River Channel Floor',
    firmware: 'operational_node',
    batteryMv: 4050,
    linkRssi: -71,
    active: true,
    measurements: {
      temperature_c: 18.8,
      relative_humidity_pct: 82.0,
      pressure_hpa: 935.8,
      pm25_ug_m3: 34.0,
      pm10_ug_m3: 51.0,
      wind_speed_mps: 1.8,
    },
    flashCommand: 'python esp32/tools/flash_esp32.py --role slave --node-id 2',
  },
];

export default function MeshTopologyPanel() {
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [scenario, setScenario] = useState('baseline');
  const [copiedId, setCopiedId] = useState(null);

  const nNodes = nodes.length;
  // Byzantine Agreement Quorum: floor(2/3 * N) + 1
  const quorumNeeded = Math.floor((2 * nNodes) / 3) + 1;

  // Evaluate consensus based on scenario
  let agreeingCount = 0;
  let domainsCount = 2;
  let consensusStatus = 'CORROBORATED';
  let consensusReason = 'All nodes agree on normal baseline conditions.';
  let badgeClass = 'badge-success';

  if (scenario === 'baseline') {
    agreeingCount = nNodes;
    consensusStatus = 'NORMAL_BASELINE';
    consensusReason = `${agreeingCount} of ${nNodes} nodes corroborate normal atmospheric conditions. Quorum satisfied.`;
    badgeClass = 'badge-success';
  } else if (scenario === 'isolated_glitch') {
    // Only Node 1 flags an extreme condition; others remain normal
    agreeingCount = 1;
    consensusStatus = 'SUPPRESSED_FALSE_ALARM';
    consensusReason = `Single-node anomaly on Slave 1 (1 of ${nNodes} votes). Byzantine quorum (${quorumNeeded}) NOT met. Alarm safely suppressed to prevent false panic.`;
    badgeClass = 'badge-warning';
  } else if (scenario === 'catchment_hazard') {
    // All nodes detect severe coordinated storm updraft
    agreeingCount = nNodes;
    consensusStatus = 'CORROBORATED_HAZARD';
    consensusReason = `Coordinated rapid pressure plunge and wind convergence confirmed across all ${nNodes} nodes and ${domainsCount} independent failure domains. Quorum satisfied.`;
    badgeClass = 'badge-danger';
  }

  // Calculate Spatial Lapse Rate between Slave 1 (Ridge: 1280m) and Slave 2 (Basin: 710m)
  const ridgeNode = nodes.find((n) => n.nodeId === 1) || nodes[1] || nodes[0];
  const basinNode = nodes.find((n) => n.nodeId === 2) || nodes[2] || nodes[0];
  const deltaZ_km = Math.max(0.001, (ridgeNode.elevationM - basinNode.elevationM) / 1000.0);
  const deltaT = ridgeNode.measurements.temperature_c - basinNode.measurements.temperature_c;
  const lapseRate_C_per_km = (deltaT / deltaZ_km).toFixed(2);
  const deltaP = (basinNode.measurements.pressure_hpa - ridgeNode.measurements.pressure_hpa).toFixed(1);
  const windShear = Math.abs(ridgeNode.measurements.wind_speed_mps - basinNode.measurements.wind_speed_mps).toFixed(1);

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleApplyScenario = (type) => {
    setScenario(type);
    if (type === 'baseline') {
      setNodes(INITIAL_NODES);
    } else if (type === 'isolated_glitch') {
      setNodes([
        INITIAL_NODES[0],
        {
          ...INITIAL_NODES[1],
          measurements: {
            ...INITIAL_NODES[1].measurements,
            pressure_hpa: 820.0, // Abrupt unrealistic plunge
            pm10_ug_m3: 1850.0, // Optical sensor obstruction
            wind_speed_mps: 34.5,
          },
        },
        INITIAL_NODES[2],
      ]);
    } else if (type === 'catchment_hazard') {
      setNodes([
        {
          ...INITIAL_NODES[0],
          measurements: {
            ...INITIAL_NODES[0].measurements,
            pressure_hpa: 918.0, // Rapid -12.5 hPa drop
            wind_speed_mps: 16.5,
          },
        },
        {
          ...INITIAL_NODES[1],
          measurements: {
            ...INITIAL_NODES[1].measurements,
            pressure_hpa: 861.0, // Severe drop
            wind_speed_mps: 26.8, // Convective gust
          },
        },
        {
          ...INITIAL_NODES[2],
          measurements: {
            ...INITIAL_NODES[2].measurements,
            pressure_hpa: 921.0,
            wind_speed_mps: 14.2,
          },
        },
      ]);
    }
  };

  const handleAddSlaveNode = () => {
    const nextIndex = nodes.length;
    const newNode = {
      id: `indra-slave-0${nextIndex}`,
      nodeId: nextIndex,
      name: `Catchment Peripheral Unit ${nextIndex}`,
      role: 'SLAVE_SENSOR',
      roleLabel: `Peripheral Slave (Node ${nextIndex})`,
      location: `Sub-Catchment Station ${nextIndex}`,
      lat: +(31.71 + (Math.random() - 0.5) * 0.05).toFixed(4),
      lon: +(76.93 + (Math.random() - 0.5) * 0.05).toFixed(4),
      elevationM: Math.round(750 + Math.random() * 600),
      terrain: 'Catchment Slope Sub-basin',
      firmware: 'operational_node',
      batteryMv: Math.round(3900 + Math.random() * 250),
      linkRssi: -Math.round(60 + Math.random() * 20),
      active: true,
      measurements: {
        temperature_c: +(15 + Math.random() * 4).toFixed(1),
        relative_humidity_pct: Math.round(75 + Math.random() * 15),
        pressure_hpa: +(900 + Math.random() * 30).toFixed(1),
        pm25_ug_m3: +(20 + Math.random() * 15).toFixed(1),
        pm10_ug_m3: +(35 + Math.random() * 20).toFixed(1),
        wind_speed_mps: +(2 + Math.random() * 6).toFixed(1),
      },
      flashCommand: `python esp32/tools/flash_esp32.py --role slave --node-id ${nextIndex}`,
    };
    setNodes([...nodes, newNode]);
  };

  const handleResetNodes = () => {
    setNodes(INITIAL_NODES);
    setScenario('baseline');
  };

  return (
    <div className="mesh-topology-container">
      <div className="reading-note" role="note">
        Reference pilot layout with design values, not live measurements. Real readings from
        your boards are in the <strong>Live sensors</strong> tab.
      </div>
      {/* Mesh Configuration Header */}
      <div className="mesh-header-card">
        <div className="mesh-header-title">
          <div className="mesh-title-row">
            <h4>Catchment Multi-Node Mesh Network</h4>
            <span className="mesh-scale-badge">
              Current Pilot: 1 Master + 2 Slaves &bull; Scalable to N Nodes (Max 512)
            </span>
          </div>
          <p className="mesh-header-desc">
            Autonomous distributed sensing across elevation gradients. The Master Node aggregates peripheral sensor frames over
            <strong> ESP-NOW / LoRa</strong> using the zero-heap <strong>82-byte HMAC-SHA256</strong> wire protocol, executing
            Byzantine consensus and edge ML forecasting locally.
          </p>
        </div>

        {/* Dynamic Byzantine Quorum & Spatial Physics Bar */}
        <div className="mesh-summary-metrics">
          <div className="mesh-metric-tile">
            <small>Active Topology</small>
            <strong>1 Master + {nNodes - 1} Slaves (N={nNodes})</strong>
          </div>
          <div className="mesh-metric-tile">
            <small>Byzantine Quorum (M-of-N)</small>
            <strong>{agreeingCount} / {quorumNeeded} Needed ({((agreeingCount / nNodes) * 100).toFixed(0)}%)</strong>
          </div>
          <div className="mesh-metric-tile">
            <small>Vertical Lapse Rate (∇T)</small>
            <strong>{lapseRate_C_per_km} °C/km</strong>
          </div>
          <div className="mesh-metric-tile">
            <small>Catchment Pressure ΔP</small>
            <strong>{deltaP} hPa</strong>
          </div>
          <div className="mesh-metric-tile">
            <small>Spatial Wind Shear</small>
            <strong>{windShear} m/s</strong>
          </div>
        </div>
      </div>

      {/* Consensus & False-Alarm Rejection Status Banner */}
      <div className={`mesh-consensus-banner ${badgeClass}`}>
        <div className="consensus-status-line">
          <span className="consensus-icon">
            {scenario === 'baseline' ? '🛡️' : scenario === 'isolated_glitch' ? '⚠️' : '🚨'}
          </span>
          <div>
            <strong>Consensus State: {consensusStatus}</strong>
            <p>{consensusReason}</p>
          </div>
        </div>
        <div className="consensus-protocol-meta">
          <span>Quorum Rule: <code>M = ⌊2/3 N⌋ + 1</code></span>
          <span>Crypto: <code>HMAC-SHA256</code> (82 Bytes)</span>
        </div>
      </div>

      {/* Interactive Scenario & Scaling Controls */}
      <div className="mesh-controls-bar">
        <div className="scenario-btn-group">
          <span className="controls-label">Test Scenarios:</span>
          <button
            type="button"
            className={`btn-scenario ${scenario === 'baseline' ? 'active' : ''}`}
            onClick={() => handleApplyScenario('baseline')}
          >
            🟢 Normal Baseline
          </button>
          <button
            type="button"
            className={`btn-scenario ${scenario === 'isolated_glitch' ? 'active' : ''}`}
            onClick={() => handleApplyScenario('isolated_glitch')}
            title="Demonstrates how single-node glitches are suppressed by Byzantine quorum"
          >
            🟡 Isolated Glitch on Slave 1 (Suppress False Alarm)
          </button>
          <button
            type="button"
            className={`btn-scenario ${scenario === 'catchment_hazard' ? 'active' : ''}`}
            onClick={() => handleApplyScenario('catchment_hazard')}
            title="Demonstrates coordinated catchment cloudburst confirmation"
          >
            🔴 Corroborated Catchment Hazard
          </button>
        </div>

        <div className="mesh-scaling-actions">
          <button type="button" className="btn-add-node" onClick={handleAddSlaveNode}>
            ➕ Add Peripheral Slave (Node {nNodes})
          </button>
          {nNodes > 3 && (
            <button type="button" className="btn-reset-nodes" onClick={handleResetNodes}>
              Reset to 3-Node Pilot
            </button>
          )}
        </div>
      </div>

      {/* Node Grid */}
      <div className="mesh-nodes-grid">
        {nodes.map((node) => {
          const isMaster = node.role === 'MASTER_GATEWAY';
          return (
            <div key={node.id} className={`mesh-node-card ${isMaster ? 'master-card' : 'slave-card'}`}>
              <div className="node-card-top">
                <div>
                  <span className={`node-role-badge ${isMaster ? 'badge-master' : 'badge-slave'}`}>
                    {node.roleLabel}
                  </span>
                  <h5 className="node-card-name">{node.name}</h5>
                  <span className="node-card-location">{node.location}</span>
                </div>
                <div className="node-power-info">
                  <span className="battery-badge">🔋 {(node.batteryMv / 1000).toFixed(2)}V</span>
                  {!isMaster && <span className="rssi-badge">📶 {node.linkRssi} dBm</span>}
                </div>
              </div>

              {/* Node Geographical Positioning */}
              <div className="node-geo-strip">
                <span>📍 {node.lat.toFixed(4)}°N, {node.lon.toFixed(4)}°E</span>
                <span>⛰️ {node.elevationM} m ({node.terrain})</span>
              </div>

              {/* Real-Time Sensor Telemetry Matrix */}
              <div className="node-telemetry-matrix">
                <div className="tel-cell">
                  <small>Temp</small>
                  <strong>{node.measurements.temperature_c}°C</strong>
                </div>
                <div className="tel-cell">
                  <small>Humidity</small>
                  <strong>{node.measurements.relative_humidity_pct}%</strong>
                </div>
                <div className="tel-cell">
                  <small>Pressure</small>
                  <strong>{node.measurements.pressure_hpa} hPa</strong>
                </div>
                <div className="tel-cell">
                  <small>PM2.5</small>
                  <strong>{node.measurements.pm25_ug_m3} µg/m³</strong>
                </div>
                <div className="tel-cell">
                  <small>PM10</small>
                  <strong>{node.measurements.pm10_ug_m3} µg/m³</strong>
                </div>
                <div className="tel-cell">
                  <small>Wind</small>
                  <strong>{node.measurements.wind_speed_mps} m/s</strong>
                </div>
              </div>

              {/* Firmware & Flashing Command Footer */}
              <div className="node-card-footer">
                <div className="firmware-tag">
                  Firmware: <code>{node.firmware}</code>
                </div>
                <button
                  type="button"
                  className="btn-copy-flash"
                  onClick={() => handleCopy(node.flashCommand, node.id)}
                  title="Copy 1-command hardware flashing instruction"
                >
                  {copiedId === node.id ? '✓ Flashing Command Copied!' : '📋 Copy Flash Command'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

