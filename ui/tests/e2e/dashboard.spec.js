import { test, expect } from "@playwright/test";
const screenshots =
  process.env.INDRA_SCREENSHOT_DIR || "test-results/screenshots";
async function connected(page) {
  await page.goto("/");
  await expect(page.getByRole("status")).toContainText("Connected");
  await expect(
    page.getByRole("heading", { name: "Mandi", exact: true }),
  ).toBeVisible();
}
async function view(page, name) {
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("button", { name, exact: true })
    .click();
}

test("observations show Mandi forecasts and clearly labeled synthetic hazard assessments", async ({
  page,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);
  await expect(page).toHaveTitle("INDRA — Local weather");
  await expect(page.locator(".data-context")).toContainText("Open-Meteo Mandi model-grid data");
  await expect(page.locator(".data-context")).toContainText("not physical sensor readings");
  await expect(page.locator(".sensor-cell")).toHaveCount(6);
  await expect(
    page.getByRole("heading", { name: "Six hours ahead" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Weather pattern scores" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Himalayan hazard scenarios" })).toBeVisible();
  await expect(page.locator('[aria-label="Weather pattern scores"]')).toContainText("not event probabilities");
  await expect(page.locator('[aria-label="Hazard scenarios"]')).toContainText("not calibrated probabilities");
  await expect(page.locator(".main-content")).not.toContainText(
    "research prototype",
  );
  await expect(page.locator(".main-content")).not.toContainText(
    "india_mandi_tabular_v2",
  );
  await expect(page.locator(".main-content")).toContainText("simulated");
  await expect(page.locator(".main-content")).toContainText("of simulated outcomes under central assumptions");
  const scenarios = page.locator('[aria-label="Hazard scenarios"]');
  if (await scenarios.locator("[data-testid^='scenario-']").count()) {
    await expect(scenarios).toContainText("Drier assumptions");
    await expect(scenarios).toContainText("Wetter assumptions");
    await expect(scenarios).toContainText("OpenMeteo");
    await expect(scenarios).toContainText("seed");
    await expect(scenarios).toContainText("lightning");
    await scenarios.locator(".hazard-explanation > summary").click();
    await expect(scenarios).toContainText("Research used");
    await scenarios.locator(".parameter-provenance > summary").click();
    await expect(scenarios).toContainText("engineering assumptions");
  }
  const patterns = page.locator('[aria-label="Weather pattern scores"]');
  await patterns.locator(".score-explanation summary").click();
  await expect(patterns).toContainText("synthetic episodes");
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
  await expect(page.getByRole("status")).toContainText("Offline · Mandi data saved", {
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
  await expect(page.locator(".technical-details")).toContainText("Open-Meteo modeled grid");
  await expect(page.locator(".system-view")).not.toContainText("SYNTHETIC ENGINEERING DEMO");
  await expect(page.locator(".system-view")).not.toContainText("Storm risk");
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
  expect(nodes).toHaveLength(1);
  await page.route("**/api/nodes", (r) => r.fulfill({ json: [] }));
  await expect(page.locator(".node-row")).toHaveCount(0, { timeout: 20000 });
  await expect(page.getByRole("heading", { name: "Choose a location" })).toBeVisible();
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

test("one Mandi API point does not create unsupported area heatmaps", async ({
  page,
}, info) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);
  await view(page, "Parameters");
  await expect(page.locator(".parameter-card")).toHaveCount(6);
  await expect(page.locator(".parameter-maps")).toContainText("An area map needs at least three locations");
  await expect(page.locator(".parameter-empty")).toHaveCount(6);
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
  await expect(page.locator(".map-legend")).toContainText("More locations are needed");
  await expect(page.locator(".leaflet-overlay-pane path")).toHaveCount(1);
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

test("google authentication flow logs in and out successfully", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);

  // 1. Click header auth button
  const authBtn = page.locator(".auth-header-btn");
  await expect(authBtn).toContainText("Sign in with Google");
  await authBtn.click();

  // 2. Auth modal opens
  const modal = page.locator(".auth-modal-card");
  await expect(modal).toBeVisible();
  await expect(modal.getByRole("heading", { name: "Sign in to INDRA" })).toBeVisible();

  // 3. Click 1-Click Sign-in
  await modal.locator(".btn-quick-operator").click();

  // 4. Modal closes and header displays user identity
  await expect(modal).not.toBeVisible();
  await expect(authBtn).toContainText("Local Demo Operator");
  await expect(authBtn).toHaveClass(/logged-in/);

  // 5. Open profile modal again
  await authBtn.click();
  await expect(modal).toBeVisible();
  await expect(modal.getByRole("heading", { name: "Local Operator Session" })).toBeVisible();
  await expect(modal.locator(".auth-badge-verified")).toContainText("Local Operator Identity");

  // 6. Sign out
  await modal.locator(".btn-signout").click();
  await expect(modal).not.toBeVisible();
  await expect(authBtn).toContainText("Sign in with Google");
  await expect(authBtn).not.toHaveClass(/logged-in/);

  expect(errors).toEqual([]);
});

test("api explorer displays and executes endpoints across subsystems", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await connected(page);

  // 1. Navigate to APIs tab
  await view(page, "APIs");
  await expect(page.locator(".api-explorer-wrap")).toBeVisible();
  await expect(page.getByRole("heading", { name: "API & Model Endpoints" })).toBeVisible();

  // 2. Verify subsystem tabs
  const groupTabs = page.locator(".api-group-btn");
  await expect(groupTabs).toHaveCount(5);
  await expect(groupTabs.nth(0)).toContainText("Telemetry");
  await expect(groupTabs.nth(1)).toContainText("Spatial");
  await expect(groupTabs.nth(2)).toContainText("Machine Learning");
  await expect(groupTabs.nth(3)).toContainText("Provenance");
  await expect(groupTabs.nth(4)).toContainText("Pan-India");

  // 3. Test executing /api/nodes
  const execBtn = page.locator(".btn-execute-api");
  await expect(execBtn).toBeVisible();
  await execBtn.scrollIntoViewIfNeeded();
  await execBtn.click();

  // 4. Verify live response output
  const responsePanel = page.locator(".api-response-panel");
  await expect(responsePanel.locator(".status-chip")).toContainText("200 OK");
  await expect(responsePanel.locator(".json-viewer")).toContainText("mandi-api-current");

  // 5. Switch to Spatial Heatmap subsystem
  await groupTabs.nth(1).click();
  await expect(page.locator(".api-stage-header h3")).toContainText("/api/kriging/heatmap");
  await execBtn.scrollIntoViewIfNeeded();
  await execBtn.click();
  await expect(responsePanel.locator(".status-chip")).toContainText("200 OK");
  await expect(responsePanel.locator(".json-viewer")).toContainText("FeatureCollection");

  expect(errors).toEqual([]);
});
