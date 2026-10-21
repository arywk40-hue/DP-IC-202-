// Check the running historical Mandi application, not synthetic UI fixtures.
import assert from 'node:assert/strict';
import {mkdirSync, writeFileSync} from 'node:fs';
import {resolve, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from '@playwright/test';

const base = process.env.INDRA_MANDI_URL || 'http://127.0.0.1:5173';
const backend = process.env.INDRA_MANDI_BACKEND_URL || 'http://127.0.0.1:8080';
const output = resolve(process.env.INDRA_SCREENSHOT_DIR || fileURLToPath(
  new URL('../../../reports/mandi_pipeline_v2', import.meta.url)));
const browser = await chromium.launch({channel:process.env.CI ? 'chromium' : 'chrome'});
const receipt = {checkedAt:new Date().toISOString(),
  evidence:'HISTORICAL_MANDI_MODELED_REPLAY_NOT_FIELD_ACCURACY', checks:[]};
try {
  mkdirSync(output,{recursive:true});
  for (const [name,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}]]) {
    const context = await browser.newContext({viewport});
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);
    await page.getByText('API connected',{exact:true}).waitFor();
    await page.locator('.telemetry-panel').getByText('Mandi tabular ensemble v2',{exact:true}).waitFor();
    assert.match(await page.locator('.research-banner').first().innerText(),/HISTORICAL MODELED DATA/);
    const status = await (await page.request.get(`${base}/api/status`)).json();
    const node = await (await page.request.get(`${base}/api/nodes/mandi-api-grid/telemetry`)).json();
    assert.equal(status.syntheticDemo,false);
    assert.equal(status.meshNodeCount,1);
    assert.equal(node.forecastStatus,'HYBRID_READY');
    assert.equal(node.forecastHistoryRows,25);
    assert.equal(node.sourceClass,'modeled_grid');
    assert.equal(node.pressureReference,'grid_surface');
    assert.equal(node.stale,true);
    assert.ok(Object.values(node.risks).every(risk=>risk.abstain && risk.probability===null));
    const lab = await (await page.request.get(`${base}/api/model-lab`)).json();
    assert.equal(lab.active_model,'india_mandi_tabular_v2');
    assert.equal(lab.data_rows,35520);
    if (process.env.INDRA_EXPECT_ONLINE === '1') {
      assert.equal(lab.online.enabled,true);
      assert.equal(lab.online.role,'SHADOW_ONLY_OFFLINE_OUTPUTS_UNCHANGED');
    }
    await page.locator('.forecast-components summary').click();
    await page.locator('.model-lab > summary').click();
    await page.getByRole('table',{name:'Forecast model comparison'}).waitFor();
    await page.screenshot({path:join(output,`mandi-${name}.png`),fullPage:true});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth));
    assert.deepEqual(errors,[]);
    receipt.checks.push({viewport:name,url:base,model:node.forecastModel.id,status:node.forecastStatus,
      historyRows:node.forecastHistoryRows,nodeId:node.id,sourceClass:node.sourceClass,
      pressureReference:node.pressureReference,stale:node.stale,forecastTimestamp:node.forecastTimestamp,
      input:node.sensors,forecast6h:node.forecast6h,online:lab.online,
      hazardAbstentions:Object.keys(node.risks),pageErrors:errors});
    await context.close();
  }
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(backend);
  await page.locator('.telemetry-panel').getByText('Mandi tabular ensemble v2',{exact:true}).waitFor();
  receipt.backendServedUi = true;
  await context.close();
  writeFileSync(join(output,'local_browser_verification.json'),JSON.stringify(receipt,null,2)+'\n');
  console.log('Mandi replay: desktop/mobile, hybrid, source labels, historical/stale state and hazard abstention PASSED.');
  console.log('Evidence:',output);
} finally {
  await browser.close();
}
