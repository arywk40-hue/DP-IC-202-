// Verify the actual current model-grid feed; these are not physical sensors.
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
    assert.match(await page.locator(".data-context").innerText(), /weather-model estimates/);
    assert.equal(await page.locator(".sensor-cell").count(), 6);
    const t = await (await page.request.get(base + "/api/nodes/mandi-api-current/telemetry")).json();
    assert.equal(t.sourceClass, "modeled_grid");
    assert.equal(t.forecastStatus, "HYBRID_READY");
    assert.equal(t.forecastHistoryRows, 25);
    assert.equal(t.syntheticDemo, false);
    assert.ok(t.timestamp <= Date.now());
    assert.ok(Date.now() - t.timestamp < 2 * 3600 * 1000);
    assert.equal(t.hazardScenarios.probability, null);
    assert.equal(t.hazardScenarios.public_alerts_enabled, false);
    await page.getByRole("heading", {name:"Hazard scenarios",exact:true}).waitFor();
    await page.getByRole("navigation").getByRole("button", {name:"System",exact:true}).click();
    await page.locator(".model-lab > summary").click();
    await page.getByTestId("online-timing").waitFor();
    assert.match(await page.getByTestId("online-timing").innerText(), /do not establish six-hour forecasting accuracy/);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: join(output, "current-" + name + ".png"), fullPage: true });
    assert.deepEqual(errors, []);
    checks.push({viewport: name, node: t.id, timestamp: t.timestamp, source: t.sourceClass, status:t.forecastStatus, forecast6h:t.forecast6h});
    await context.close();
  }
  writeFileSync(join(output, "browser.json"), JSON.stringify({checked_at:new Date().toISOString(),evidence:"CURRENT_MODEL_GRID_NOT_STATION_VALIDATION",checks},null,2)+"\n");
  console.log("Current Mandi desktop/mobile feed, six inputs, forecast and scenario provenance: PASSED");
} finally {
  await browser.close();
}
