import React, { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { locationName, sourceName } from "../api/presentation";
import { parameterColor, PARAMETERS } from "../api/parameter-colors";

function healthColor(lastSeen, interval = 300) {
  const age = Date.now() - lastSeen;
  if (age < Math.max(120, interval) * 1000) return "#47785d";
  if (age < Math.max(120, interval * 2) * 1000) return "#b4934b";
  return "#a7987d";
}

export default function MapView({
  nodes,
  heatmap,
  heatmapStatus,
  heatmapReason,
  selectedId,
  showHeatmap,
  onSelect,
  parameter,
  onParameterChange,
  onToggleHeatmap,
}) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const markersRef = useRef({});
  const heatLayerRef = useRef(null);
  const lastBoundsKeyRef = useRef("");

  useEffect(() => {
    if (mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
      scrollWheelZoom: false,
      // Views unmount this map. Leaflet 1.9's delayed zoom transition can
      // otherwise access a removed pane after rapid navigation.
      zoomAnimation: false,
    }).setView([31.71, 76.933], 14);

    const grid = L.gridLayer({
      tileSize: 256,
      attribution: "Local coordinate grid",
    });
    grid.createTile = function (coords) {
      const tile = document.createElement("canvas");
      tile.width = tile.height = 256;
      const ctx = tile.getContext("2d");
      ctx.fillStyle = "#edf1eb";
      ctx.fillRect(0, 0, 256, 256);
      for (let i = 0; i <= 256; i += 64) {
        ctx.strokeStyle = i % 256 === 0 ? "#d2ddd0" : "#e1e8de";
        ctx.lineWidth = 0.7;
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, 256);
        ctx.moveTo(0, i);
        ctx.lineTo(256, i);
        ctx.stroke();
      }
      const ll = map.unproject(
        L.point(coords.x * 256, coords.y * 256),
        coords.z,
      );
      ctx.fillStyle = "#8a9b89";
      ctx.font = "10px system-ui";
      ctx.fillText(`${ll.lat.toFixed(3)}°, ${ll.lng.toFixed(3)}°`, 10, 18);
      return tile;
    };
    grid.addTo(map);
    if (import.meta.env.VITE_OSM_TILES === "true")
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>contributors',
        maxZoom: 19,
      }).addTo(map);

    mapRef.current = map;
    let active = true;
    const frame = requestAnimationFrame(() => {
      if (active) map.invalidateSize();
    });
    const resizeObserver = new ResizeObserver(() => {
      if (active) map.invalidateSize({ pan: false });
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      active = false;
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      map.stop();
      map.remove();
      mapRef.current = null;
      markersRef.current = {};
      heatLayerRef.current = null;
      lastBoundsKeyRef.current = "";
    };
  }, []);

  // Auto-fit bounds whenever the coordinates of the nodes change or update
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !nodes.length) return;

    const validNodes = nodes.filter(
      (n) =>
        typeof n.lat === "number" &&
        !isNaN(n.lat) &&
        typeof n.lng === "number" &&
        !isNaN(n.lng),
    );
    if (!validNodes.length) return;

    const boundsKey = validNodes
      .map((n) => `${n.id}:${n.lat.toFixed(5)},${n.lng.toFixed(5)}`)
      .sort()
      .join("|");

    if (boundsKey !== lastBoundsKeyRef.current) {
      lastBoundsKeyRef.current = boundsKey;
      if (validNodes.length === 1) {
        map.setView([validNodes[0].lat, validNodes[0].lng], 15, {
          animate: false,
        });
      } else {
        const bounds = L.latLngBounds(validNodes.map((n) => [n.lat, n.lng]));
        map.fitBounds(bounds.pad(0.35), { maxZoom: 16, animate: false });
      }
    }
  }, [nodes]);

  // Smoothly pan to the selected node when clicked in the list or map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId) return;
    const target = nodes.find((n) => n.id === selectedId);
    if (
      target &&
      typeof target.lat === "number" &&
      typeof target.lng === "number"
    ) {
      map.panInside([target.lat, target.lng], {
        animate: false,
        padding: [35, 35],
      });
    }
  }, [selectedId, nodes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const seen = new Set();
    nodes
      .filter((n) => Number.isFinite(n.lat) && Number.isFinite(n.lng))
      .forEach((node) => {
        seen.add(node.id);
        const color = healthColor(node.lastSeen, node.reportingIntervalSeconds);
        let marker = markersRef.current[node.id];

        if (!marker) {
          marker = L.circleMarker([node.lat, node.lng], {
            radius: 9,
            weight: 2,
            fillOpacity: 0.9,
          })
            .addTo(map)
            .on("click", () => onSelect(node.id));
          markersRef.current[node.id] = marker;
        } else {
          marker.setLatLng([node.lat, node.lng]);
        }

        const age = Date.now() - node.lastSeen;
        const offline =
          age >=
          Math.max(120, (node.reportingIntervalSeconds || 300) * 2) * 1000;
        marker.setStyle({
          color: node.id === selectedId ? "#ffffff" : color,
          fillColor: color,
          radius: node.id === selectedId ? 12 : offline ? 11 : 9,
          weight: node.id === selectedId || offline ? 3 : 2,
        });

        marker.bindPopup(renderPopup(node, onSelect), {
          maxWidth: 220,
          autoPanPadding: [12, 12],
        });
      });

    Object.keys(markersRef.current).forEach((id) => {
      if (!seen.has(id)) {
        map.removeLayer(markersRef.current[id]);
        delete markersRef.current[id];
      }
    });
  }, [nodes, selectedId, onSelect]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    if (!showHeatmap || !heatmap?.features?.length) return;
    heatLayerRef.current = L.geoJSON(heatmap, {
      style: (f) => ({
        color: parameterColor(f.properties.intensity),
        fillColor: parameterColor(f.properties.intensity),
        weight: f.geometry.type === "LineString" ? 8 : 0,
        fillOpacity: 0.62,
      }),
      onEachFeature: (f, layer) =>
        layer.bindTooltip(
          `${PARAMETERS[f.properties.channel]?.[0]}: ${f.properties.value.toFixed(2)} ${f.properties.unit} (interpolated)`,
        ),
    }).addTo(map);
    Object.values(markersRef.current).forEach((marker) =>
      marker.bringToFront(),
    );
  }, [heatmap, showHeatmap]);

  return (
    <section className="map-wrap" aria-label="Location map">
      <div className="map-toolbar">
        <div>
          <span className="eyebrow">Area view</span>
          <strong>
            {nodes.length} {nodes.length === 1 ? "location" : "locations"}
          </strong>
        </div>
        <div className="map-actions">
          <label className="map-layer-label">
            <span className="sr-only">Map parameter</span>
            <select
              aria-label="Map parameter"
              value={parameter}
              onChange={(e) => onParameterChange(e.target.value)}
            >
              {Object.entries(PARAMETERS).map(([key, [name]]) => (
                <option key={key} value={key}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            className={`heat-toggle ${showHeatmap ? "heat-toggle-on" : ""}`}
            aria-pressed={showHeatmap}
            onClick={onToggleHeatmap}
          >
            Color map {showHeatmap ? "on" : "off"}
          </button>
        </div>
      </div>
      <div className="map-stage">
        <div ref={containerRef} className="map-view" />
        <div className="map-legend">
          {showHeatmap && heatmap?.features?.length > 0 ? (
            <>
              <div className="legend-title">
                {PARAMETERS[heatmap.channel]?.[0]} <span>{heatmap.unit}</span>
              </div>
              <div className="heat-scale" />
              <div className="heat-scale-labels">
                <span>{heatmap.minimum?.toFixed(1)}</span>
                <span>{heatmap.maximum?.toFixed(1)}</span>
              </div>
              <small>Estimated between readings</small>
            </>
          ) : (
            <>
              <div className="legend-title">Location readings</div>
              <small>
                {nodes.length < 2
                  ? "More locations are needed to estimate an area."
                  : "Select a measurement and turn on the color map."}
              </small>
            </>
          )}
          <div className="map-health-key">
            <span>
              <i className="health-dot health-ok" /> Recent
            </span>
            <span>
              <i className="health-dot health-late" /> Older reading
            </span>
          </div>
        </div>
        {!nodes.length && (
          <div className="map-empty">
            <strong>Your locations, on one map.</strong>
            <p>Readings will appear here as they become available.</p>
          </div>
        )}
      </div>
    </section>
  );
}
function renderPopup(node, onSelect) {
  const el = document.createElement("div");
  el.className = "map-popup";
  const title = document.createElement("strong");
  title.textContent = locationName(node);
  const meta = document.createElement("p");
  meta.textContent = sourceName(node.sourceClass);
  const view = document.createElement("button");
  view.className = "map-popup-btn";
  view.textContent = "View readings";
  view.onclick = () => onSelect(node.id);
  el.append(title, meta, view);
  return el;
}
