# Master REST API — HLS integration contract

Owner: **Mannan (High Level Systems)**  
Consumers: Master firmware (`api.cpp`), Communications (payload timing), Crypto (RPC ACK behaviour)

The dashboard (`mesh-dashboard`) treats this file as the source of truth. If firmware cannot match a field name, add a mapper in `src/api/client.js` — do not fork the React components.

Golden JSON: `example_payloads.json`  
Lab stand-in: `cd mesh-dashboard && node mock-master.mjs` then set `MASTER_BASE_URL` to `http://127.0.0.1:8080`.

See `High_Level_Systems_Complete.md` §5 for shapes, opcodes, polling budget, and silent-reject rules.
