# High Level Systems — Dashboard & Hosting Architecture Report
**Assignee:** Manan

## 1. Design Iterations
*For each design approach being considered, fill out the following block:*

### Design No: 01
**System Architecture:** A React 18 + Leaflet.js Progressive Web App (PWA) running on the admin's device, communicating with the Master Node (ESP32-S3-N16R8) over its local WiFi Access Point via a stateless JSON REST API. The dashboard is installed once as a static bundle (via Service Worker) and thereafter only exchanges lightweight JSON with the Master — no HTML/CSS/JS is ever served by the Master itself.

**A. Cross-Functional Integration Constraints (CRITICAL)**
*How does this specific design accommodate the Master Node's hardware and mesh requirements?*
* **API Surface:** Consumes 5 endpoints exposed by the Master — `/api/nodes`, `/api/nodes/{id}/telemetry`, `/api/kriging/heatmap`, `/api/rpc/{id}`, `/api/status`.
* **Compute Budget on Master:** Master runs on `lwIP` (Espressif's minimal embedded TCP/IP stack), optimized for small, frequent requests — not multi-megabyte static assets. Dashboard must never expect the Master to serve its own app bundle.
* **Request Load Ceiling:** Master Node's API is stress-tested to 10 req/s (per pipeline task 3.3 acceptance criteria). Dashboard polling intervals must stay well under this — node list/status polled every 5–10s, Kriging heatmap fetched every ~60s or on-demand only.
* **RPC Command Set Dependency:** Dashboard's command UI is directly coupled to the 8 RPC opcodes defined in firmware (`CMD_FORCE_INFERENCE`, `CMD_SEND_TELEMETRY`, `CMD_UPDATE_THRESH`, `CMD_SET_SLEEP_PERIOD`, `CMD_DISABLE_PERIPH`, `CMD_REBOOT`, `CMD_SYNC_NONCE`, `CMD_GET_BATTERY`) — any firmware change to this enum requires a matching dashboard update.
* **Connectivity Model:** No cellular/cloud path exists. Dashboard must function entirely over the Master's local WiFi AP and degrade gracefully to cached data when disconnected.

**B. Technology Stack & Procurement**
| S.No | Component Name | Technology (e.g., React, Leaflet) | Procurement Type (Library/Built In-House) | Maturity/Support Rating |
|---|---|---|---|---|
| 1 | Frontend Framework | React 18 | Library | High — large ecosystem, long-term support |
| 2 | Mapping/Heatmap Layer | Leaflet.js + Leaflet.heat plugin | Library | High — mature, lightweight, offline-capable |
| 3 | Offline App Shell | Service Worker (Workbox or custom) | Library/Built In-House | Medium — requires careful cache versioning |
| 4 | Local Data Cache | IndexedDB | Browser-native API | High — standard, well-supported |
| 5 | API Client | Fetch API / Axios | Library | High |
| 6 | Backend API | Custom JSON REST API (`lwIP`, firmware-side) | Built In-House | Medium — constrained by ESP32-S3 resources |

**C. Hosting & Deployment Feasibility**
| S.No | Component | Deployment Method | Runs on Master Node? | Runs on Admin Device? | Feasible on ESP32-S3? | Ease of Implementation (1-10) | Est. Dev Time |
|---|---|---|---|---|---|---|---|
| 1 | REST API (5 endpoints) | Embedded in Master firmware | Yes | No | Yes (within `lwIP` limits) | 6 | ~1 week |
| 2 | React/Leaflet PWA bundle | Pre-built static bundle, installed once | No | Yes | N/A (never hosted on Master) | 7 | ~1–2 weeks |
| 3 | Service Worker offline packaging | Client-side | No | Yes | N/A | 5 | ~2–3 days |

**D. Estimated Effort/Cost (Software Only)**
| S.No | Item | Effort (person-days) | Total Quantity | Total Effort |
|---|---|---|---|---|
| 1 | React frontend build (NodeList, MapView, TelemetryPanel, RpcMenu) | 6 | 1 | 6 days |
| 2 | RPC injection UI + response handling | 2 | 1 | 2 days |
| 3 | Service Worker + IndexedDB offline caching | 3 | 1 | 3 days |
| 4 | Master-side REST API (`api.cpp`) | 5 | 1 | 5 days |
| 5 | Node registry + MicroSD persistence (`registry.cpp`) | 3 | 1 | 3 days |

## 2. Component Failure Modes & Mitigation
*Provide a table for EACH major component/mechanism in the shortlisted design.*
| Component Name | Failure Mode | Reason for Failure | Proposed Fix / Mitigation |
|---|---|---|---|
| WiFi AP Link | Admin device disconnects mid-session | Range limit of ESP32 AP, admin walks out of range, AP restart | Dashboard shows persistent "last synced X min ago" banner; auto-retries connection in background; falls back to IndexedDB cache |
| RPC Command Delivery | Command silently rejected by Slave Node | Corrupted MIC or nonce outside expected window (per crypto module's silent-rejection design) | Dashboard treats "no ACK within timeout" as failure, not success; explicitly shows "command not confirmed" state |
| Master Node API | Overloaded under simultaneous requests | Too many polling clients or burst of node reports exceeding 10 req/s ceiling | Conservative, staggered client-side polling intervals; requests queued rather than fired in parallel |
| Kriging Heatmap | Misleading interpolation over offline node's location | Node goes offline but Kriging engine still interpolates using neighboring nodes' data as if valid | Cross-reference `/api/nodes` last-seen timestamps against heatmap region; visually flag interpolated zones near stale/offline nodes |
| Cached Data Display | Admin mistakes cached (offline) data for live data | IndexedDB fallback activates automatically during disconnection | Persistent, color-coded "live" vs "cached" indicator on every data panel — not a one-time toast |
| Node Reporting | Stale telemetry after node hardware/battery failure | Node stops reporting; `CMD_GET_BATTERY` never responds | Node list flags nodes silent beyond ~2x expected 5-min reporting cycle as "possibly offline" |
| App Bundle | Service Worker serves outdated app after firmware/API update | Cached app shell mismatched with new API contract (e.g. new RPC command added) | Version number embedded in app bundle, checked against `/api/status` response; prompts force-refresh on mismatch |

## 3. Minimum Prerequisites (Non-Compromisable)
*The design is rejected automatically if it cannot pass ALL of these checks.*
| Requirement | Value / Standard | Checks Out? (Y/N) |
|---|---|---|
| 1. Cloud/Cellular Independence | Dashboard MUST function entirely over local WiFi AP, zero cloud dependency | Y |
| 2. Master Node Load | API request rate MUST stay within 10 req/s stress-test ceiling | Y |
| 3. Offline Usability | Dashboard MUST remain viewable (cached data) when disconnected from Master | Y |
| 4. Master Resource Budget | Master MUST NOT serve HTML/CSS/JS bundles — JSON only | Y |
| 5. RPC Integrity Handling | Dashboard MUST NOT assume RPC success without explicit ACK/response | Y |
| 6. Data Freshness Transparency | UI MUST visibly distinguish live vs. cached data at all times | Y |
| 7. Command Set Sync | Dashboard's RPC menu MUST match the 8-opcode firmware enum exactly | Y |

## 4. Shortlisting & Evaluation
| Design No | Design Name | Evaluation Comments | Meets all Prerequisites? | Priority / Rank |
|---|---|---|---|---|
| 01 | React + Leaflet PWA, thin JSON API on Master | Matches project's no-cloud philosophy; offline-capable; constrained but proven fit for ESP32-S3 resource envelope | Y | 1 |

## 5. Final Conclusion & Handoff
**Final chosen design:** Design 01 — a React 18 + Leaflet.js Progressive Web App, installed once on the admin's device via Service Worker, communicating with the Master Node's stateless JSON REST API (5 endpoints) over local WiFi. Offline resilience is handled via IndexedDB caching with explicit live/cached UI indicators. RPC commands are dispatched through the dashboard but treated as unconfirmed until an explicit response/ACK is received, in line with the crypto module's silent-rejection behavior.

**Constraints still needed from other teams before finalizing implementation:**
- **From Machine Learning (Ariyan):** Exact structure/fields of the `SensorDataStruct` and Anomaly Index output, so the `TelemetryPanel` and node marker status colors can be defined precisely.
- **From Electronics & Power (Aditi):** Confirmed battery voltage range and reporting units for `CMD_GET_BATTERY`, so the dashboard's battery indicator thresholds (e.g. low-battery warning) are calibrated correctly.
- **From Communications (Abhinav):** Confirmed AODV route-discovery timing (~500ms re-discovery) and typical polling window (2s/hour), to set realistic RPC command timeout values in the dashboard UI.
- **From Cryptographical Module (Anushka):** Exact error/response behavior on MIC or nonce mismatch — whether the Master ever surfaces a rejection reason to the API, or if it is truly silent end-to-end — to finalize how "command failed" states are communicated to the admin.
