/**
 * ESP32 Master Station Test Firmware for Mesh Dashboard
 * 
 * Hardware: ESP32 / ESP32-S3
 * Purpose: Acts as the Master Node Wi-Fi Access Point and serves the REST API
 *          needed by the React Dashboard (DP_Dashboard / DP_Mesh_Dashboard_Handoff).
 * 
 * Instructions:
 * 1. Open this file in Arduino IDE.
 * 2. Select Board: "ESP32 Dev Module" (or your specific ESP32 board).
 * 3. Update the `lat` and `lng` coordinates below to your testing coordinates.
 * 4. Upload to the ESP32.
 * 5. Connect your laptop to Wi-Fi SSID "MeshMaster_AP" (password: "mesh12345").
 * 6. Open http://192.168.4.1/api/nodes in your browser to verify.
 */

#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "MeshMaster_AP";
const char* password = "mesh12345";

WebServer server(80);

// =========================================================================
// CONFIGURE YOUR TEST NODE COORDINATES HERE
// =========================================================================
struct NodeData {
  const char* id;
  const char* name;
  double lat;
  double lng;
  float battery;
  unsigned long lastSeenAgoMs;
};

// Update these latitudes and longitudes to test any location in the world:
NodeData meshNodes[] = {
  { "01", "Node 01 — Ridge",  31.7076, 76.9366, 3.31, 15000 },
  { "02", "Node 02 — Valley", 31.7112, 76.9420, 3.18, 45000 },
  { "03", "Node 03 — Slope",  31.7050, 76.9300, 3.05, 120000 },
  { "04", "Node 04 — Field",  31.7140, 76.9280, 3.28, 5000 }
};
const int NUM_NODES = sizeof(meshNodes) / sizeof(meshNodes[0]);

// =========================================================================
// HELPER: Send JSON with CORS headers
// =========================================================================
void sendJson(int code, const String& jsonBody) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(code, "application/json", jsonBody);
}

// Handle CORS OPTIONS preflight
void handleOptions() {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "Content-Type");
  server.send(204);
}

// =========================================================================
// ENDPOINT 1: GET /api/status
// =========================================================================
void handleStatus() {
  unsigned long uptime = millis() / 1000;
  String json = "{";
  json += "\"uptimeSeconds\":" + String(uptime) + ",";
  json += "\"batteryVoltage\":3.34,";
  json += "\"meshNodeCount\":" + String(NUM_NODES) + ",";
  json += "\"appVersion\":\"0.1.0\"";
  json += "}";
  sendJson(200, json);
}

// =========================================================================
// ENDPOINT 2: GET /api/nodes
// =========================================================================
void handleGetNodes() {
  unsigned long now = millis();
  String json = "[";
  for (int i = 0; i < NUM_NODES; i++) {
    // Generate simulated timestamp in ms
    unsigned long lastSeen = (1726250000UL * 1000UL) + (now - meshNodes[i].lastSeenAgoMs);

    json += "{";
    json += "\"id\":\"" + String(meshNodes[i].id) + "\",";
    json += "\"name\":\"" + String(meshNodes[i].name) + "\",";
    json += "\"lat\":" + String(meshNodes[i].lat, 6) + ",";
    json += "\"lng\":" + String(meshNodes[i].lng, 6) + ",";
    json += "\"battery\":" + String(meshNodes[i].battery, 2) + ",";
    json += "\"lastSeen\":" + String(lastSeen);
    json += "}";
    if (i < NUM_NODES - 1) json += ",";
  }
  json += "]";
  sendJson(200, json);
}

// =========================================================================
// ENDPOINT 3: GET /api/nodes/{id}/telemetry
// =========================================================================
void handleTelemetry() {
  String uri = server.uri(); // e.g. /api/nodes/01/telemetry
  String nodeId = "01";
  int startIdx = uri.indexOf("/nodes/") + 7;
  int endIdx = uri.indexOf("/telemetry");
  if (startIdx >= 7 && endIdx > startIdx) {
    nodeId = uri.substring(startIdx, endIdx);
  }

  String json = "{";
  json += "\"id\":\"" + nodeId + "\",";
  json += "\"timestamp\":" + String(1726250000UL * 1000UL + millis()) + ",";
  json += "\"anomalyIndex\":0,";
  json += "\"anomalyLabel\":\"Normal\",";
  json += "\"battery\":3.31,";
  json += "\"sensors\":{";
  json += "\"temperature_c\":23.5,";
  json += "\"humidity_pct\":55.0,";
  json += "\"pressure_hpa\":912.4,";
  json += "\"voc_iaq\":60,";
  json += "\"wind_speed_ms\":2.4,";
  json += "\"wind_dir_deg\":180,";
  json += "\"rain_mm\":0.0,";
  json += "\"pm25_ugm3\":14,";
  json += "\"pm10_ugm3\":22,";
  json += "\"uv_index\":4,";
  json += "\"radiation_cpm\":16";
  json += "}";
  json += "}";
  sendJson(200, json);
}

// =========================================================================
// ENDPOINT 4: GET /api/kriging/heatmap
// =========================================================================
void handleHeatmap() {
  String json = "{\"type\":\"FeatureCollection\",\"features\":[";
  for (int i = 0; i < NUM_NODES; i++) {
    json += "{\"type\":\"Feature\",";
    json += "\"geometry\":{\"type\":\"Point\",\"coordinates\":[" + String(meshNodes[i].lng, 6) + "," + String(meshNodes[i].lat, 6) + "]},";
    json += "\"properties\":{\"intensity\":0.35}}";
    if (i < NUM_NODES - 1) json += ",";
  }
  json += "]}";
  sendJson(200, json);
}

// =========================================================================
// ENDPOINT 5: POST /api/rpc/{id}
// =========================================================================
void handleRpc() {
  sendJson(200, "{\"ok\":true,\"msg\":\"RPC command acknowledged by Master\"}");
}

// =========================================================================
// SETUP & LOOP
// =========================================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n[Master] Booting ESP32 Mesh Master Station...");

  // Start Wi-Fi Access Point
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  IPAddress IP = WiFi.softAPIP();

  Serial.println("[Master] Access Point started successfully!");
  Serial.print("[Master] SSID: ");
  Serial.println(ssid);
  Serial.print("[Master] AP IP address: ");
  Serial.println(IP); // Default: 192.168.4.1

  // Set up routes
  server.on("/api/status", HTTP_GET, handleStatus);
  server.on("/api/nodes", HTTP_GET, handleGetNodes);
  server.on("/api/kriging/heatmap", HTTP_GET, handleHeatmap);
  
  // Wildcard / regex routes or prefix matching
  server.onNotFound([]() {
    String uri = server.uri();
    if (server.method() == HTTP_OPTIONS) {
      handleOptions();
      return;
    }
    if (uri.startsWith("/api/nodes/") && uri.endsWith("/telemetry")) {
      handleTelemetry();
      return;
    }
    if (uri.startsWith("/api/rpc/")) {
      handleRpc();
      return;
    }
    sendJson(404, "{\"error\":\"Not Found\"}");
  });

  server.begin();
  Serial.println("[Master] HTTP REST API Server listening on port 80.");
}

void loop() {
  server.handleClient();
}
