import { test, expect } from '@playwright/test';
const screenshots = process.env.INDRA_SCREENSHOT_DIR || '../../reports/mandi_pipeline_v2';

test('saved model, six channels, three experimental assessments and unsupported RPC', async ({page}, info) => {
  const errors=[]; page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Rain condition risk'})).toBeVisible();
  await expect(page.locator('.sensor-cell')).toHaveCount(6);
  await expect(page.locator('.risk-card')).toHaveCount(3);
  await expect(page.locator('.source-banner')).toContainText('SYNTHETIC DEMO');
  await expect(page.locator('.telemetry-panel')).toContainText('india_mandi_tabular_v2');
  await expect(page.locator('.telemetry-panel')).toContainText('Mandi tabular ensemble v2');
  await expect(page.locator('.telemetry-panel')).toContainText('HYBRID_READY');
  await expect(page.locator('.telemetry-panel')).toContainText('25/25');
  await page.locator('.forecast-components summary').click();
  await expect(page.locator('.forecast-components')).toContainText('lightgbm');
  await expect(page.locator('.telemetry-panel')).toContainText('Calibration: unavailable');
  await page.locator('.node-row').filter({hasText:'demo-02'}).locator('.node-row-name').click();
  await expect(page.locator('.risk-card').filter({hasText:'Snowstorm risk'})).toContainText('local warning candidate');
  await page.locator('.node-row').filter({hasText:'demo-03'}).locator('.node-row-name').click();
  await expect(page.locator('.risk-card').filter({hasText:'Cloudburst risk'})).toContainText('local warning candidate');
  await page.screenshot({path:`${screenshots}/${info.project.name}.png`,fullPage:true});
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
  await page.screenshot({path:`${screenshots}/storm-${info.project.name}.png`,fullPage:true});
  expect((await panel.innerText()).toLowerCase()).not.toMatch(/probability|chance|likelihood|accuracy|%/);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});

test('replacing the imported nodes selects an available node instead of retaining a removed ID', async ({page}) => {
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  await expect(page.locator('.telemetry-panel')).toContainText('demo-01');
  const nodes = await (await page.request.get('/api/nodes')).json();
  await page.route('**/api/nodes', route => route.fulfill({json:nodes.filter(n=>n.id==='demo-02')}));
  await expect(page.locator('.node-row')).toHaveCount(1,{timeout:20000});
  await expect(page.locator('.telemetry-panel')).toContainText('demo-02',{timeout:20000});
  await expect(page.locator('.telemetry-panel')).toContainText('HYBRID_READY');
});

test('model workspace shows mixed comparison and honest delayed-learning state',async({page},info)=>{
  await page.goto('/');
  await expect(page.getByText('API connected',{exact:true})).toBeVisible();
  const lab=page.locator('.model-lab');
  await expect(lab.locator('summary').first()).toContainText('35,520 modeled hours');
  await lab.locator('summary').first().click();
  await expect(lab.getByRole('table',{name:'Forecast model comparison'})).toBeVisible();
  await expect(lab).toContainText('Improvements are mixed');
  await expect(lab).toContainText('Worker not configured');
  await lab.getByLabel('Comparison period').selectOption('future_test');
  await expect(lab.locator('tbody tr')).toHaveCount(6);
  await page.screenshot({path:`${screenshots}/model-lab-${info.project.name}.png`,fullPage:true});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
