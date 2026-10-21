import { test, expect } from "@playwright/test";
const screenshots =
  process.env.INDRA_SCREENSHOT_DIR || "../../reports/ui_refresh_v1";
async function connected(page) {
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("Connected");
  await expect(
    page.getByRole("heading", { name: "Location 01", exact: true }),
  ).toBeVisible();
}
async function view(page, name) {
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name, exact: true })
    .click();
}

test("observations prioritize readings and patterns while retaining honest data provenance", async ({
  page,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);
  await expect(page).toHaveTitle("INDRA — Local weather");
  await expect(page.locator(".data-context")).toContainText(
    "simulated readings",
  );
  await expect(page.locator(".sensor-cell")).toHaveCount(6);
  await expect(
    page.getByRole("heading", { name: "Six hours ahead" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Weather patterns" }),
  ).toBeVisible();
  await expect(page.locator(".main-content")).not.toContainText(
    "research prototype",
  );
  await expect(page.locator(".main-content")).not.toContainText(
    "india_mandi_tabular_v2",
  );
  await expect(
    page.getByRole("button", { name: "RPC", exact: true }),
  ).toHaveCount(0);
  await page.locator(".score-explanation summary").click();
  await expect(page.locator(".score-explanation")).toContainText(
    "not real-event probabilities",
  );
  await page.screenshot({
    path: `${screenshots}/${info.project.name}.png`,
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("connection loss labels saved readings and maps instead of suggesting they are live", async ({
  page,
}) => {
  await connected(page);
  await page.route("**/api/**", (r) => r.abort());
  await expect(page.getByRole("status")).toContainText("Offline · saved data", {
    timeout: 20000,
  });
  await expect(page.locator(".stale-notice")).toContainText("Saved reading");
  await view(page, "Parameters");
  await expect(page.locator(".parameter-maps")).toContainText(
    "Showing saved maps",
  );
});

test("rapid map zoom and navigation do not leave callbacks on a removed map", async ({ page }) => {
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await connected(page);
  for (let i = 0; i < 6; i++) {
    await page.getByRole("button", {name:"Zoom in",exact:true}).click();
    await view(page, "System");
    await expect(page.locator(".system-view")).toBeVisible();
    await view(page, "Observations");
    await expect(page.getByRole("region", {name:"Location map"})).toBeVisible();
  }
  // Drain Leaflet's 250 ms transition fallback to catch removed-pane callbacks.
  await page.waitForTimeout(350);
  expect(errors).toEqual([]);
});

test("hazard scenarios show three simulation fractions without promoting them to event probabilities", async ({ page }, info) => {
  await connected(page);
  const panel = page.getByRole("region", { name: "Hazard scenarios" });
  await expect(panel).toContainText("not the chance of a real event");
  for (const id of ["cloudburst", "flash_flood", "landslide"]) {
    await expect(panel.getByTestId(`scenario-${id}`)).toContainText("Central case");
    await expect(panel.getByTestId(`scenario-${id}`)).toContainText("Across assumptions");
  }
  await panel.getByText("How are these calculated?").click();
  await expect(panel).toContainText("not a confidence interval");
  await expect(panel).toContainText("No alerts are sent");
  const payload = await (await page.request.get("/api/nodes/demo-01/telemetry")).json();
  expect(payload.hazardScenarios.probability).toBeNull();
  expect(payload.hazardScenarios.public_alerts_enabled).toBe(false);
  await panel.screenshot({path: `${screenshots}/hazard-scenarios-${info.project.name}.png`});
});

test("technical model evidence and rule checks remain accessible in System", async ({
  page,
}, info) => {
  await connected(page);
  await view(page, "System");
  await expect(page.locator(".technical-details")).toContainText(
    "india_mandi_tabular_v2",
  );
  await expect(page.locator(".technical-details")).toContainText(
    "HYBRID_READY",
  );
  await expect(page.locator(".technical-details")).toContainText("25/25");
  await page.locator(".forecast-components summary").click();
  await expect(page.locator(".forecast-components")).toContainText("lightgbm");
  await page.locator(".legacy-assessments > summary").click();
  await expect(page.locator(".risk-card")).toHaveCount(3);
  await expect(page.locator(".technical-details")).toContainText(
    "Calibration: unavailable",
  );
  await expect(
    page.getByRole("button", { name: "Device commands", exact: true }),
  ).toHaveCount(0);
  const panel = page.locator(".storm-risk-panel");
  await panel.locator("summary").first().click();
  await expect(
    panel.getByRole("img", { name: "t2m feature heatmap" }),
  ).toBeVisible();
  await expect(panel.getByTestId("anomaly-marker")).toHaveCount(3);
  await page.screenshot({
    path: `${screenshots}/system-${info.project.name}.png`,
    fullPage: true,
  });
});

test("a removed location is replaced by an available selection", async ({
  page,
}) => {
  await connected(page);
  const nodes = await (await page.request.get("/api/nodes")).json();
  await page.route("**/api/nodes", (r) =>
    r.fulfill({ json: nodes.filter((n) => n.id === "demo-02") }),
  );
  await expect(page.locator(".node-row")).toHaveCount(1, { timeout: 20000 });
  await expect(
    page.getByRole("heading", { name: "Location 02", exact: true }),
  ).toBeVisible({ timeout: 20000 });
  await view(page, "System");
  await expect(page.locator(".technical-details")).toContainText(
    "HYBRID_READY",
  );
});

test("model comparison retains mixed results and separate online-learning state", async ({
  page,
}, info) => {
  await connected(page);
  await view(page, "System");
  const lab = page.locator(".model-lab");
  await expect(lab.locator("summary").first()).toContainText(
    "35,520 modeled hours",
  );
  await lab.locator("summary").first().click();
  await expect(
    lab.getByRole("table", { name: "Forecast model comparison" }),
  ).toBeVisible();
  await expect(lab).toContainText("Improvements are mixed");
  await expect(lab).toContainText("Worker not configured");
  await lab.getByLabel("Comparison period").selectOption("future_test");
  await expect(lab.locator("tbody tr")).toHaveCount(6);
  await page.screenshot({
    path: `${screenshots}/model-${info.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("all parameter maps lead back to the selected geographic overlay", async ({
  page,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);
  await view(page, "Parameters");
  await expect(page.locator(".parameter-card svg")).toHaveCount(6);
  await expect(
    page.getByRole("img", {
      name: "Temperature interpolated heatmap",
      exact: true,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: `${screenshots}/parameters-${info.project.name}.png`,
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Show Wind heatmap", exact: true })
    .click();
  await expect(
    page
      .getByRole("navigation")
      .getByRole("button", { name: "Observations", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByRole("combobox", { name: "Map parameter" }),
  ).toHaveValue("wind_speed_mps");
  await expect(page.locator(".heat-toggle")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator(".map-legend")).toContainText("m/s");
  await expect(page.locator(".leaflet-overlay-pane path")).not.toHaveCount(0);
  await page.screenshot({
    path: `${screenshots}/map-${info.project.name}.png`,
    fullPage: true,
  });
  expect(errors).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
