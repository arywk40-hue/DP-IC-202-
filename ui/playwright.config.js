import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
const python = process.env.INDRA_PYTHON || 'python3';
const projectPython = process.env.INDRA_PYTHON ||
  (existsSync('../.venv/bin/python') ? '.venv/bin/python' : python);
const port = process.env.INDRA_E2E_PORT || '8081';
export default defineConfig({
  testDir: './tests/e2e', timeout: 30000, workers: 1,
  use: { baseURL: `http://127.0.0.1:${port}`, channel: process.env.CI ? 'chromium' : 'chrome', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: {width:1440,height:1000} } },
    { name: 'mobile', use: { viewport: {width:390,height:844}, isMobile:true, hasTouch:true } }
  ],
  webServer: {
    command: `cd .. && "${projectPython}" -m server.tests.e2e_dashboard --port ${port}`,
    url: `http://127.0.0.1:${port}/api/status`, timeout:60000, reuseExistingServer:false
  }
});
