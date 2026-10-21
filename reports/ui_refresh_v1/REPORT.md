# INDRA interface refresh

21 October 2026. The interface now uses a light map-first layout, three clear
views, readable location names, compact measurements and a separate forecast.
Technical model details moved into System. Simulated, archived, older and saved
readings remain identifiable. No model weights or source identities were changed
by the visual redesign.

Verified workflows: desktop/mobile observations, parameter-map selection,
geographic overlays, weather-pattern scores, saved offline readings, location
replacement, model comparisons and technical evidence. The actual local Mandi
application and separate twelve-location simulated application were both checked.
See `verification.json` and the browser receipts in this folder.

The larger software change also implements six supported IDW measurement
surfaces and a ten-category synthetic-trained LightGBM/MLP classifier. See
`reports/weather_features_v1/REPORT.md`. Synthetic category performance remains
separate from real event accuracy.

Public deployment has not occurred. Hosting, live ingestion, physical device
tests and independent local event validation remain as described in
[the handoff guide](../../docs/UI_AND_DEPLOYMENT_STATUS.md).
