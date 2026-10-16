# INDRA six-channel dashboard

Adapted from the supplied DP Mesh Dashboard handoff. Original teammate files are
preserved in `docs/reference/dp_mesh_dashboard_handoff/` at the repository root.
The working API version is **0.3.0**.

From the repository root, install `requirements-dashboard.txt` into your Python
environment. In this directory run `npm ci`. Then, from the root:

```sh
python scripts/run_himachal_demo.py --offline
```

Open http://127.0.0.1:8080. The demo is labelled synthetic throughout. It runs the
saved Mandi neural/history-XGBoost/ridge six-hour hybrid and the current rain/snowstorm/cloudburst
risk rules. Scores are not calibrated hazard probabilities. Hardware/RPC and
spatial surfaces are unavailable until their integration and validation pass.

For imported native snapshots use `--observations /absolute/path/snapshots.json`.
For development start `python -m server.dashboard --demo` in the root and
`npm run dev` here; Vite proxies `/api` to port 8080. No silent mock fallback.

Full setup, input contract, limitations and tests:
[Dashboard integration](../../docs/HIMACHAL_DASHBOARD_INTEGRATION.md).

```sh
npm test
npm run test:e2e
npm run build
```
