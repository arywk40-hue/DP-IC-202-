import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png'
});

function healthColor(lastSeen) {
  const age = Date.now() - lastSeen;
  if (age < 5 * 60 * 1000) return '#4fd1c5';
  if (age < 2 * 5 * 60 * 1000) return '#f0b429';
  return '#f2545b';
}

export default function MapView({
  nodes,
  heatmap,
  selectedId,
  showHeatmap,
  onSelect,
  onOpenRpc
}) {
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const markersRef = useRef({});
  const heatLayerRef = useRef(null);
  const lastBoundsKeyRef = useRef('');

  useEffect(() => {
    if (mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true
    }).setView([31.71, 76.933], 14);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {                            
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>contributors',                                                                                   
      maxZoom: 19                                                                                  
    }).addTo(map);  

    mapRef.current = map;
    requestAnimationFrame(() => map.invalidateSize());

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Auto-fit bounds whenever the coordinates of the nodes change or update
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !nodes.length) return;

    const validNodes = nodes.filter(
      (n) => typeof n.lat === 'number' && !isNaN(n.lat) && typeof n.lng === 'number' && !isNaN(n.lng)
    );
    if (!validNodes.length) return;

    const boundsKey = validNodes
      .map((n) => `${n.id}:${n.lat.toFixed(5)},${n.lng.toFixed(5)}`)
      .sort()
      .join('|');

    if (boundsKey !== lastBoundsKeyRef.current) {
      lastBoundsKeyRef.current = boundsKey;
      if (validNodes.length === 1) {
        map.setView([validNodes[0].lat, validNodes[0].lng], 15, { animate: true });
      } else {
        const bounds = L.latLngBounds(validNodes.map((n) => [n.lat, n.lng]));
        map.fitBounds(bounds.pad(0.35), { maxZoom: 16, animate: true });
      }
    }
  }, [nodes]);

  // Smoothly pan to the selected node when clicked in the list or map
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedId) return;
    const target = nodes.find((n) => n.id === selectedId);
    if (target && typeof target.lat === 'number' && typeof target.lng === 'number') {
      map.panTo([target.lat, target.lng], { animate: true, duration: 0.6 });
      const marker = markersRef.current[selectedId];
      if (marker && !marker.isPopupOpen()) {
        marker.openPopup();
      }
    }
  }, [selectedId, nodes]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const seen = new Set();
    nodes.forEach((node) => {
      seen.add(node.id);
      const color = healthColor(node.lastSeen);
      let marker = markersRef.current[node.id];

      if (!marker) {
        marker = L.circleMarker([node.lat, node.lng], {
          radius: 9,
          weight: 2,
          fillOpacity: 0.9
        })
          .addTo(map)
          .on('click', () => onSelect(node.id));
        markersRef.current[node.id] = marker;
      } else {
        marker.setLatLng([node.lat, node.lng]);
      }

      const age = Date.now() - node.lastSeen;
      const offline = age >= 2 * 5 * 60 * 1000;
      marker.setStyle({
        color: node.id === selectedId ? '#ffffff' : color,
        fillColor: color,
        radius: node.id === selectedId ? 12 : offline ? 11 : 9,
        weight: node.id === selectedId || offline ? 3 : 2
      });

      marker.bindPopup(renderPopup(node, onSelect, onOpenRpc));
    });

    Object.keys(markersRef.current).forEach((id) => {
      if (!seen.has(id)) {
        map.removeLayer(markersRef.current[id]);
        delete markersRef.current[id];
      }
    });
  }, [nodes, selectedId, onSelect, onOpenRpc]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (heatLayerRef.current) {
      map.removeLayer(heatLayerRef.current);
      heatLayerRef.current = null;
    }

    if (!showHeatmap || !heatmap?.length) return;

    const points = heatmap.map((p) => [p.lat, p.lng, p.intensity]);
    heatLayerRef.current = L.heatLayer(points, {
      radius: 28,
      blur: 22,
      maxZoom: 16,
      minOpacity: 0.25,
      gradient: { 0.2: '#1c2b45', 0.45: '#4fd1c5', 0.7: '#f0b429', 1.0: '#f2545b' }
    }).addTo(map);
  }, [heatmap, showHeatmap]);

  return (
    <div className="map-wrap">
      <div ref={containerRef} className="map-view" />
      <div className="map-legend">
        <div className="legend-title">Node health</div>
        <div className="legend-row">
          <span className="health-dot health-ok" /> Live (&lt;5 min)
        </div>
        <div className="legend-row">
          <span className="health-dot health-late" /> Late
        </div>
        <div className="legend-row">
          <span className="health-dot health-offline" /> Offline
        </div>
        <div className="legend-title" style={{ marginTop: 10 }}>
          Kriging intensity
        </div>
        <div className="heat-scale" />
        <div className="heat-scale-labels">
          <span>Calm</span>
          <span>Anomaly</span>
        </div>
      </div>
    </div>
  );
}

function renderPopup(node, onSelect, onOpenRpc) {
  const el = document.createElement('div');
  el.className = 'map-popup';
  el.innerHTML = `<strong>${node.name}</strong><br/>Battery: ${node.battery.toFixed(2)} V`;
  const row = document.createElement('div');
  row.className = 'map-popup-actions';
  const view = document.createElement('button');
  view.textContent = 'View telemetry';
  view.className = 'map-popup-btn';
  view.onclick = () => onSelect(node.id);
  const cmd = document.createElement('button');
  cmd.textContent = 'Send RPC…';
  cmd.className = 'map-popup-btn';
  cmd.onclick = () => onOpenRpc(node.id);
  row.append(view, cmd);
  el.appendChild(row);
  return el;
}
