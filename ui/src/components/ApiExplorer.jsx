import React, { useState } from 'react';
import {
  getNodes,
  getTelemetry,
  getStatus,
  getHeatmap,
  getAllParameterMaps,
  getModelLab,
  getProvenance,
  getAuthConfig,
  getAuthMe,
} from '../api/client';

const API_GROUPS = [
  {
    id: 'telemetry',
    title: '1. Mandi API & Telemetry',
    subtitle: 'Open-Meteo weather and air-quality model-grid data for Mandi',
    endpoints: [
      {
        id: 'get-nodes',
        method: 'GET',
        path: '/api/nodes',
        description: 'Returns the single Mandi Open-Meteo model-grid location and data freshness.',
        action: () => getNodes(),
      },
      {
        id: 'get-telemetry',
        method: 'GET',
        path: '/api/nodes/{id}/telemetry',
        description: 'Retrieves the six Mandi modeled-grid channels, available history, and six-hour forecast.',
        hasParam: true,
        paramName: 'Node ID',
        defaultParam: 'mandi-api-current',
        action: (param) => getTelemetry(param || 'mandi-api-current'),
      },
      {
        id: 'get-status',
        method: 'GET',
        path: '/api/status',
        description: 'Mandi API connection status, latest data time, and active forecast model.',
        action: () => getStatus(),
      },
    ],
  },
  {
    id: 'spatial',
    title: '2. Spatial Interpolation & Heatmap APIs',
    subtitle: 'Continuous 2D spatial estimation and Leaflet GeoJSON layer generation',
    endpoints: [
      {
        id: 'get-heatmap',
        method: 'GET',
        path: '/api/kriging/heatmap?channel={channel}',
        description: 'Returns a spatial estimate when enough synchronized Mandi-area points are available; one point alone produces no surface.',
        hasSelect: true,
        selectOptions: [
          { value: 'temperature_c', label: 'Temperature (°C)' },
          { value: 'relative_humidity_pct', label: 'Humidity (%)' },
          { value: 'pressure_hpa', label: 'Pressure (hPa)' },
          { value: 'pm25_ug_m3', label: 'PM2.5 (µg/m³)' },
          { value: 'pm10_ug_m3', label: 'PM10 (µg/m³)' },
          { value: 'wind_speed_mps', label: 'Wind Speed (m/s)' },
        ],
        defaultSelect: 'temperature_c',
        action: (channel) => getHeatmap(channel || 'temperature_c'),
      },
      {
        id: 'get-parameter-maps',
        method: 'GET',
        path: '/api/parameter-heatmaps',
        description: 'Returns six parameter maps when the connected data provides enough synchronized locations.',
        action: () => getAllParameterMaps(),
      },
    ],
  },
  {
    id: 'models',
    title: '3. Machine Learning & Forecasting APIs',
    subtitle: 'Forecast model, local Mandi hindcast evaluation, and shadow update status',
    endpoints: [
      {
        id: 'get-model-lab',
        method: 'GET',
        path: '/api/model-lab',
        description: 'Evaluation metrics across chronological cohorts, blend weights, and online shadow learner updates.',
        action: () => getModelLab(),
      },
    ],
  },
  {
    id: 'security',
    title: '4. Provenance, Audit & Google Auth APIs',
    subtitle: 'Cryptographic data integrity receipts, batch hash chains, and Google OAuth identity',
    endpoints: [
      {
        id: 'get-provenance',
        method: 'GET',
        path: '/api/provenance',
        description: 'Hash-linked SQLite transaction audit batch proofs and EVM anchor metadata.',
        action: () => getProvenance(),
      },
      {
        id: 'get-auth-config',
        method: 'GET',
        path: '/api/auth/config',
        description: 'Exposes Google OAuth2 client credentials and active gateway auth mode.',
        action: () => getAuthConfig(),
      },
      {
        id: 'get-auth-me',
        method: 'GET',
        path: '/api/auth/me',
        description: 'Validates current Bearer session token and returns authenticated Google user identity.',
        action: () => getAuthMe(),
      },
    ],
  },
];

export default function ApiExplorer() {
  const [selectedGroup, setSelectedGroup] = useState('telemetry');
  const [activeEndpointId, setActiveEndpointId] = useState('get-nodes');
  const [customParams, setCustomParams] = useState({});
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [statusCode, setStatusCode] = useState(null);
  const [durationMs, setDurationMs] = useState(null);
  const [copied, setCopied] = useState(false);

  const group = API_GROUPS.find((g) => g.id === selectedGroup) || API_GROUPS[0];
  const activeEndpoint =
    group.endpoints.find((e) => e.id === activeEndpointId) || group.endpoints[0];

  const handleExecute = async () => {
    setLoading(true);
    setResponse(null);
    setStatusCode(null);
    const start = performance.now();
    try {
      const paramVal =
        customParams[activeEndpoint.id] ??
        activeEndpoint.defaultParam ??
        activeEndpoint.defaultSelect;
      const res = await activeEndpoint.action(paramVal);
      const elapsed = Math.round(performance.now() - start);
      setDurationMs(elapsed);
      setStatusCode(200);
      setResponse(res);
    } catch (err) {
      const elapsed = Math.round(performance.now() - start);
      setDurationMs(elapsed);
      setStatusCode(err.message?.includes('401') ? 401 : 500);
      setResponse({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const getCurlSnippet = () => {
    const token =
      typeof localStorage !== 'undefined'
        ? localStorage.getItem('indra_auth_token')
        : null;
    const authHeader = token ? ` -H "Authorization: Bearer ${token}"` : '';
    let path = activeEndpoint.path;
    if (activeEndpoint.hasParam) {
      path = path.replace(
        '{id}',
        customParams[activeEndpoint.id] || activeEndpoint.defaultParam || 'mandi-api-current',
      );
    }
    if (activeEndpoint.hasSelect) {
      path = path.replace(
        '{channel}',
        customParams[activeEndpoint.id] ||
          activeEndpoint.defaultSelect ||
          'temperature_c',
      );
    }
    return `curl -sS "${window.location.origin}${path}"${authHeader} | jq .`;
  };

  const handleCopyCurl = () => {
    navigator.clipboard?.writeText(getCurlSnippet());
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="api-explorer-wrap" aria-label="INDRA API Explorer">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Interactive Developer Suite</span>
          <h2>API & Model Endpoints</h2>
        </div>
        <span className="section-tag">REST &bull; JSON &bull; GeoJSON</span>
      </div>
      <p className="api-explorer-lead">
        Read the connected Open-Meteo Mandi data, six-hour forecasts, parameter maps,
        and local data provenance. API values are modeled grid estimates, not station readings.
      </p>

      {/* Subsystem tabs */}
      <div className="api-group-nav" role="tablist">
        {API_GROUPS.map((g) => (
          <button
            key={g.id}
            type="button"
            role="tab"
            aria-selected={selectedGroup === g.id}
            className={`api-group-btn ${selectedGroup === g.id ? 'active' : ''}`}
            onClick={() => {
              setSelectedGroup(g.id);
              setActiveEndpointId(g.endpoints[0].id);
              setResponse(null);
            }}
          >
            {g.title}
          </button>
        ))}
      </div>

      <div className="api-explorer-body">
        {/* Endpoint sidebar */}
        <div className="api-endpoint-list">
          <div className="api-list-header">
            <h4>{group.title}</h4>
            <small>{group.subtitle}</small>
          </div>
          {group.endpoints.map((ep) => (
            <button
              key={ep.id}
              type="button"
              className={`api-endpoint-card ${activeEndpoint.id === ep.id ? 'selected' : ''}`}
              onClick={() => {
                setActiveEndpointId(ep.id);
                setResponse(null);
              }}
            >
              <div className="api-method-row">
                <span className={`method-badge ${ep.method.toLowerCase()}`}>
                  {ep.method}
                </span>
                <span className="endpoint-path">{ep.path}</span>
              </div>
              <p className="endpoint-desc">{ep.description}</p>
            </button>
          ))}
        </div>

        {/* Execution & Output Stage */}
        <div className="api-stage">
          <div className="api-stage-header">
            <div className="api-title-row">
              <span className={`method-badge ${activeEndpoint.method.toLowerCase()}`}>
                {activeEndpoint.method}
              </span>
              <h3>{activeEndpoint.path}</h3>
            </div>
            <p className="api-target-desc">{activeEndpoint.description}</p>
          </div>

          <div className="api-params-card">
            <div className="params-controls">
              {activeEndpoint.hasParam && (
                <label className="param-field">
                  <span>{activeEndpoint.paramName}:</span>
                  <input
                    type="text"
                    value={
                      customParams[activeEndpoint.id] ??
                      activeEndpoint.defaultParam ??
                      ''
                    }
                    onChange={(e) =>
                      setCustomParams({
                        ...customParams,
                        [activeEndpoint.id]: e.target.value,
                      })
                    }
                    placeholder={activeEndpoint.defaultParam}
                  />
                </label>
              )}

              {activeEndpoint.hasSelect && (
                <label className="param-field">
                  <span>Parameter Channel:</span>
                  <select
                    value={
                      customParams[activeEndpoint.id] ??
                      activeEndpoint.defaultSelect ??
                      ''
                    }
                    onChange={(e) =>
                      setCustomParams({
                        ...customParams,
                        [activeEndpoint.id]: e.target.value,
                      })
                    }
                  >
                    {activeEndpoint.selectOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </label>
              )}

              <button
                type="button"
                className="btn-execute-api"
                onClick={handleExecute}
                disabled={loading}
              >
                {loading ? 'Executing…' : '▶ Send Request'}
              </button>
            </div>

            <div className="api-curl-bar">
              <code>{getCurlSnippet()}</code>
              <button
                type="button"
                className="btn-copy-curl"
                onClick={handleCopyCurl}
                title="Copy curl command"
              >
                {copied ? 'Copied!' : 'Copy cURL'}
              </button>
            </div>
          </div>

          {/* Response Console */}
          <div className="api-response-panel">
            <div className="response-header">
              <span>Response Output</span>
              {statusCode && (
                <div className="response-meta">
                  <span
                    className={`status-chip ${statusCode === 200 ? 'status-ok' : 'status-err'}`}
                  >
                    {statusCode} {statusCode === 200 ? 'OK' : 'Error'}
                  </span>
                  <span className="latency-chip">{durationMs} ms</span>
                </div>
              )}
            </div>

            <div className="response-content">
              {loading && (
                <div className="response-placeholder">
                  <div className="pulse-loader" />
                  <span>Fetching live endpoint data...</span>
                </div>
              )}
              {!loading && !response && (
                <div className="response-placeholder">
                  <span>Click "▶ Send Request" above to trigger this API and view live JSON results.</span>
                </div>
              )}
              {!loading && response && (
                <pre className="json-viewer">
                  <code>{JSON.stringify(response, null, 2)}</code>
                </pre>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
