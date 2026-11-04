import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { chromium } from "@playwright/test";

const baseUrl = process.env.INDRA_LIVE_URL || "http://127.0.0.1:8094";
const output = process.env.INDRA_REPORT_PATH;
const browser = await chromium.launch({ channel: "chrome", headless: true });
const errors = [];
const views = [];
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(error.message));
  const status = await (await page.request.get(`${baseUrl}/api/status`)).json();
  const telemetry = await (
    await page.request.get(`${baseUrl}/api/nodes/mandi-api-current/telemetry`)
  ).json();
  const mapData = await (await page.request.get(`${baseUrl}/api/parameter-heatmaps`)).json();
  assert.equal(status.mandiApi.connected, true);
  assert.equal(status.adapter, "OPEN_METEO_MANDI_READ_ONLY");
  assert.equal(telemetry.sourceClass, "modeled_grid");
  assert.equal(telemetry.forecastStatus, "HYBRID_READY");
  assert.equal(Object.keys(telemetry.sensors).length, 6);
  assert.equal(mapData.status, "UNAVAILABLE");
  assert.deepEqual(Object.keys(mapData.layers), []);
  assert.equal(mapData.nodes.length, 1);

  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    await page.setViewportSize(viewport);
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    assert.match(await page.getByRole("status").innerText(), /Connected/);
    assert.equal(await page.title(), "INDRA — Local weather");
    assert.equal(await page.locator(".sensor-cell").count(), 6);
    assert.equal(await page.getByRole("heading", { name: "Six hours ahead" }).count(), 1);
    const scenarios = page.locator('[aria-label="Hazard scenarios"]');
    assert.match(await scenarios.innerText(), /not calibrated probabilities/);
    assert.match(await scenarios.innerText(), /of simulated outcomes under central assumptions/);
    assert.equal(await page.locator(".main-content").evaluate((el) => el.scrollWidth <= window.innerWidth), true);
    await page.getByRole("navigation", { name: "Main navigation" })
      .getByRole("button", { name: "Parameters", exact: true }).click();
    assert.match(await page.locator(".parameter-maps").innerText(), /An area map needs at least three locations/);
    assert.equal(await page.locator(".parameter-empty").count(), 6);
    views.push({ ...viewport, status: "PASS" });
  }
  assert.deepEqual(errors, []);
  const report = {
    schema_version: "indra_live_dashboard_browser_check_v1",
    verified_at_utc: new Date().toISOString(),
    data_evidence: "LIVE_OPEN_METEO_MODELED_GRID_NOT_PHYSICAL_SENSOR_DATA",
    browser: "Chrome via Playwright",
    browser_version: browser.version(),
    base_url: baseUrl,
    source_class: telemetry.sourceClass,
    source_id: telemetry.sourceId,
    observation_time_utc: new Date(telemetry.timestamp).toISOString(),
    forecast_target_time_utc: telemetry.forecastTimestamp,
    forecast_model_id: telemetry.forecastModel.id,
    forecast_profile_sha256: telemetry.forecastModel.profileSha256,
    channels_rendered: Object.keys(telemetry.sensors),
    map_status: mapData.status,
    map_location_count: mapData.nodes.length,
    map_layers: Object.keys(mapData.layers),
    viewport_checks: views,
    browser_errors: errors,
  };
  if (output) await writeFile(output, `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} finally {
  await browser.close();
}
