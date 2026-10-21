# INDRA interface and deployment handoff

Updated 21 October 2026. The app is presented as **INDRA — Local weather**.
The main interface no longer uses research/prototype/phase branding. Data-source
labels still distinguish simulated readings, archived modeled weather and actual
station readings. Changing the interface does not change the provenance of data.

## Current interface

- **Observations:** locations, an offline-capable geographic coordinate grid,
  selectable parameter overlays, six current readings, a six-hour numerical
  forecast and compact weather-pattern matches.
- **Parameters:** six measurement maps, ranges and units. Selecting a map returns
  to the matching geographic overlay. Unsupported areas stay unavailable.
- **System:** source identities, timestamps, forecast model/components, rule
  evidence, comparison results and separate online-learning status.

Technical IDs, calibration details and engineering checks are kept out of the
main reading flow. Unsupported device commands are not offered as functioning
controls. Older readings and saved offline data remain labelled. Times use IST.

Preview with all features: http://127.0.0.1:8082.
Downloaded historical Mandi view: http://127.0.0.1:8080.

## What remains

1. **Hosting:** choose the hosting account/service and public URL, configure HTTPS
   and persistent storage, then verify the deployed frontend and API together.
   Nothing has been publicly deployed by this UI change.
2. **Live input:** connect the actual sensor/gateway importer. Existing downloaded
   Mandi data is historical and contains one location. A live area map needs
   synchronized readings from multiple distinct locations; three noncollinear
   locations support an area, two only a connecting line.
3. **Field validation:** test real sensors/ESP32/RF and the numerical forecast on
   local outcomes. The current category model was trained on simulated patterns;
   independently observed events/non-events are needed to assess real hazard
   skill and calibrate event probabilities. No UI change establishes that skill.

The maps and category software are implemented and tested. These remaining tasks
concern hosting, live data and empirical product claims rather than missing UI
screens. The existing online learner stays in shadow mode; it is not silently
promoted into published forecasts.

## Deployment entry point

The Python server can serve the built frontend and API from one origin:

```sh
python -m pip install -r requirements-dashboard.txt
npm ci --prefix apps/indra-himachal-ui
npm run build --prefix apps/indra-himachal-ui
python -m server.dashboard --host 0.0.0.0 --port 8080 --ui apps/indra-himachal-ui/dist --db /persistent/indra/dashboard.sqlite --observations /persistent/indra/reviewed_observations.json
```

Use the host's assigned port and persistent paths in place of these examples.
The default listen address remains `127.0.0.1` for local work. No synthetic
source is automatically selected when the server starts without an input flag.
The command prepares the serving process; it does not create a sensor feed.
The existing reviewed importer must update the store when new measurements arrive.

Include the committed forecast components, category model and referenced reports
in the backend deployment. Raw training CSVs, synthetic working arrays, TabPFN,
PyTorch, credentials and local SQLite snapshots are not frontend assets.
With frontend/API split across domains, configure the API origin and server
cross-origin policy explicitly; the same-origin deployment above avoids that step.

## Verification

Browser workflows cover desktop/mobile navigation, source labels, all six maps,
saved-data handling, location replacement and access to model evidence. Runtime
checks exercise both the simulated twelve-location view and the historical Mandi
view. Screenshots and receipts are in `reports/ui_refresh_v1/`.
