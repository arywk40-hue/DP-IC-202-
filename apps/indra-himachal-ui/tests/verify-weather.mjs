// A live local synthetic application check; this does not test real event accuracy.
import assert from "node:assert/strict";
import { writeFileSync, mkdirSync } from "node:fs";
import { chromium } from "@playwright/test";
const base = process.env.INDRA_WEATHER_URL || "http://127.0.0.1:8082";
const output = process.env.INDRA_SCREENSHOT_DIR || "../../reports/ui_refresh_v1";
const browser = await chromium.launch({
  channel: process.env.CI ? "chromium" : "chrome",
});
const receipt = {
  checkedAt: new Date().toISOString(),
  evidence: "SYNTHETIC_TWELVE_LOCATION_SOFTWARE_DEMO_NOT_OBSERVED_WEATHER",
  checks: [],
};
try {
  mkdirSync(output, { recursive: true });
  for (const [name, viewport] of [
    ["desktop", { width: 1440, height: 1000 }],
    ["mobile", { width: 390, height: 844 }],
  ]) {
    const ctx = await browser.newContext({ viewport });
    const page = await ctx.newPage();
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(base);
    await page.getByRole("status").filter({ hasText: "Connected" }).waitFor();
    await page
      .getByRole("navigation")
      .getByRole("button", { name: "Parameters", exact: true })
      .click();
    await page
      .getByRole("img", {
        name: "Temperature interpolated heatmap",
        exact: true,
      })
      .waitFor();
    await page
      .getByRole("button", { name: "Show Temperature heatmap", exact: true })
      .click();
    await page
      .locator(".node-row")
      .filter({ hasText: "Location 05" })
      .getByRole("button")
      .click();
    await page.getByTestId("category-heatwave_like").waitFor();
    assert.match(
      await page.getByTestId("category-heatwave_like").getAttribute("class"),
      /category-match/,
    );
    const maps = await (
      await page.request.get(`${base}/api/parameter-heatmaps`)
    ).json();
    assert.equal(Object.keys(maps.layers).length, 6);
    assert.equal(maps.nodes.length, 12);
    await page.screenshot({
      path: `${output}/showcase-${name}.png`,
      fullPage: true,
    });
    await page.getByTestId("category-heatwave_like").scrollIntoViewIfNeeded();
    await page.screenshot({
      path: `${output}/categories-${name}.png`,
      fullPage: true,
    });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    assert.deepEqual(errors, []);
    assert.equal(overflow, false);
    receipt.checks.push({
      viewport: name,
      nodes: maps.nodes.length,
      status: maps.status,
      channels: Object.keys(maps.layers),
      heatwavePatternMatched: true,
      pageErrors: errors,
      horizontalOverflow: overflow,
    });
    await ctx.close();
  }
  writeFileSync(
    `${output}/showcase_browser.json`,
    JSON.stringify(receipt, null, 2) + "\n",
  );
  console.log(
    "Twelve-location synthetic showcase: all parameter maps and category workflow passed desktop/mobile.",
  );
} finally {
  await browser.close();
}
