import { test, expect } from '@playwright/test';

test('saved model, six channels, three experimental assessments and unsupported RPC', async ({page}, info) => {
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Rain condition risk'})).toBeVisible();
  await expect(page.locator('.sensor-cell')).toHaveCount(6);
  await expect(page.locator('.risk-card')).toHaveCount(3);
  await expect(page.locator('.source-banner')).toContainText('SYNTHETIC DEMO');
  await expect(page.locator('.telemetry-panel')).toContainText('india_mandi_hybrid_6h_v1');
  await expect(page.locator('.telemetry-panel')).toContainText('Mandi neural hybrid');
  await expect(page.locator('.telemetry-panel')).toContainText('HYBRID_READY');
  await expect(page.locator('.telemetry-panel')).toContainText('25/25');
  await page.locator('.forecast-components summary').click();
  await expect(page.locator('.forecast-components')).toContainText('residual_mlp_');
  await expect(page.locator('.telemetry-panel')).toContainText('Calibration: unavailable');
  await page.locator('.node-row').filter({hasText:'demo-02'}).locator('.node-row-name').click();
  await expect(page.locator('.risk-card').filter({hasText:'Snowstorm risk'})).toContainText('local warning candidate');
  await page.locator('.node-row').filter({hasText:'demo-03'}).locator('.node-row-name').click();
  await expect(page.locator('.risk-card').filter({hasText:'Cloudburst risk'})).toContainText('local warning candidate');
  await page.screenshot({path:`../../reports/india_mandi_hybrid_6h_v1/${info.project.name}.png`,fullPage:true});
  await page.locator('.node-row').filter({hasText:'demo-04'}).locator('.node-row-name').click();
  await expect(page.locator('.risk-card').filter({hasText:'Cloudburst risk'})).toContainText('Unknown / insufficient evidence');
  await expect(page.locator('.telemetry-panel')).toContainText('WARMING_UP_PERSISTENCE');
  await page.locator('.node-row').first().getByRole('button',{name:'RPC',exact:true}).click();
  await expect(page.locator('.rpc-menu')).toContainText('Commands are disabled');
  await expect(page.locator('.rpc-menu').getByRole('button',{name:'Send',exact:true}).first()).toBeDisabled();
  expect(errors).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test('API loss shows cached data, not current observations', async ({page}) => {
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  await expect(page.locator('.sensor-cell')).toHaveCount(6);
  await page.route('**/api/**',route=>route.abort());
  await expect(page.locator('.sync-pill')).toContainText('Cached',{timeout:20000});
  await expect(page.locator('.stale-notice')).toContainText('CACHED',{timeout:20000});
});

test('storm research outputs show gate warnings, anomaly markers and feature grid', async ({page}, info) => {
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  const panel = page.locator('.storm-risk-panel');
  await expect(panel.locator('summary').first()).toContainText('synthetic_ui_contract_fixture');
  await panel.locator('summary').first().click();
  await expect(panel).toContainText('Experimental risk score (uncalibrated)');
  await expect(panel).toContainText('SYNTHETIC ENGINEERING DEMO');
  await expect(panel.getByRole('table')).toBeVisible();
  await expect(panel.getByRole('columnheader', {name:'Neighbour-confirmed (experimental)'})).toBeVisible();
  await expect(panel.getByRole('img', {name:'t2m feature heatmap'})).toBeVisible();
  await expect(panel.getByTestId('anomaly-marker')).toHaveCount(3);
  await panel.getByRole('img').scrollIntoViewIfNeeded();
  await page.screenshot({path:`../../reports/india_mandi_hybrid_6h_v1/storm-${info.project.name}.png`,fullPage:true});
  expect((await panel.innerText()).toLowerCase()).not.toMatch(/probability|chance|likelihood|accuracy|%/);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
