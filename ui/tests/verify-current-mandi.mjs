// Verify the running Open-Meteo Mandi feed and six-channel forecast UI.
import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { chromium } from "@playwright/test";

const base = process.env.INDRA_MANDI_URL || "http://127.0.0.1:8080";
const output = resolve(process.env.INDRA_SCREENSHOT_DIR || "test-results/current-mandi");
mkdirSync(output, { recursive: true });
const browser = await chromium.launch({ channel: process.env.CI ? "chromium" : "chrome" });
const checks = [];
try {
  for (const [name, viewport] of [["desktop", { width: 1440, height: 1000 }], ["mobile", { width: 390, height: 844 }]]) {
    const context = await browser.newContext({ viewport });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(base);
    await page.getByRole("heading", { name: "Mandi", exact: true }).waitFor();
    await page.locator(".sensor-cell").first().waitFor();
    assert.equal(await page.locator(".sensor-cell").count(), 6);
    assert.match(await page.locator(".data-context").innerText(), /modeled grid|weather-model estimates/i);
    const status = await (await page.request.get(base + "/api/status")).json();
    assert.equal(status.adapter, "OPEN_METEO_MANDI_READ_ONLY");
    const telemetry = await (await page.request.get(base + "/api/nodes/mandi-api-current/telemetry")).json();
    assert.equal(telemetry.sourceClass, "modeled_grid");
    assert.equal(telemetry.syntheticDemo, false);
    assert.equal(Object.keys(telemetry.sensors).length, 6);
    assert.ok(Object.values(telemetry.sensors).every(Number.isFinite));
    assert.ok(["SYNTHETIC_SCENARIOS_ONLY", "OUTSIDE_SYNTHETIC_DOMAIN", "UNAVAILABLE"].includes(telemetry.hazardScenarios.status));
    assert.equal(telemetry.hazardScenarios.calibrated, false);
    assert.equal(telemetry.hazardScenarios.probability, null);
    assert.equal(telemetry.weatherCategories.calibrated, false);
    assert.equal(telemetry.weatherCategories.score_kind, "SYNTHETIC_PATTERN_SCORE_NOT_EVENT_PROBABILITY");
    await page.getByRole("navigation").getByRole("button", { name: "System", exact: true }).click();
    await page.locator(".model-lab > summary").click();
    await page.getByTestId("online-timing").waitFor();
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: join(output, `current-${name}.png`), fullPage: true });
    assert.deepEqual(errors, []);
    checks.push({ viewport: name, id: telemetry.id, timestamp: telemetry.timestamp, source: telemetry.sourceClass, forecastStatus: telemetry.forecastStatus });
    await context.close();
  }
  writeFileSync(join(output, "browser.json"), JSON.stringify({ checked_at: new Date().toISOString(), evidence: "OPEN_METEO_MANDI_MODELED_GRID_NOT_STATION_VALIDATION", checks }, null, 2) + "\n");
  console.log("Mandi API desktop/mobile UI, six channels, source provenance, and forecast workflow: PASSED");
} finally {
  await browser.close();
}
