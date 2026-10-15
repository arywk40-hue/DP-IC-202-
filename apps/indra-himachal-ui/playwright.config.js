import { defineConfig } from '@playwright/test';
const python = process.env.INDRA_PYTHON || 'python3';
export default defineConfig({
  testDir: './tests/e2e', timeout: 30000, workers: 1,
  use: { baseURL: 'http://127.0.0.1:8081', channel: process.env.CI ? 'chromium' : 'chrome', screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { viewport: {width:1440,height:1000} } },
    { name: 'mobile', use: { viewport: {width:390,height:844}, isMobile:true, hasTouch:true } }
  ],
  webServer: {
    command: `cd ../.. && "${python}" -m server.dashboard --demo --ui apps/indra-himachal-ui/dist --db data/himachal/dashboard_e2e.sqlite --port 8081`,
    url: 'http://127.0.0.1:8081/api/status', timeout:60000, reuseExistingServer:false
  }
});
