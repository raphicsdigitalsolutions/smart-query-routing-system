import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const dirname = __dirname;
const backendDir = path.resolve(dirname, '../backend');
const e2eDir = path.resolve(dirname, '.e2e');
const apiPort = 8100;
const appPort = 3100;
const python = path.join(backendDir, '.venv', 'Scripts', 'python.exe');

const e2eEnv = {
  ...process.env,
  ENVIRONMENT: 'development',
  DEBUG: 'false',
  DATABASE_URL: `sqlite:///${path.join(e2eDir, 'e2e.db').replaceAll('\\', '/')}`,
  JWT_SECRET_KEY: 'e2e-only-jwt-secret-not-for-production-0123456789',
  ACCESS_TOKEN_EXPIRE_MINUTES: '1440',
  EMAIL_NOTIFICATIONS_ENABLED: 'false',
  WHATSAPP_ENABLED: 'false',
  BACKGROUND_WORKER_ENABLED: 'false',
  ATTACHMENT_STORAGE_DIR: path.join(e2eDir, 'attachments'),
  E2E_API_PORT: String(apiPort),
};

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '.e2e/report' }]],
  outputDir: '.e2e/results',
  use: {
    baseURL: `http://127.0.0.1:${appPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `"${python}" e2e_server.py`,
      cwd: backendDir,
      url: `http://127.0.0.1:${apiPort}/health`,
      env: e2eEnv,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `npx next start --hostname 127.0.0.1 --port ${appPort}`,
      cwd: dirname,
      url: `http://127.0.0.1:${appPort}/login`,
      env: {
        ...process.env,
        API_BASE_URL: `http://127.0.0.1:${apiPort}/api/v1`,
        NEXT_PUBLIC_API_BASE_URL: `http://127.0.0.1:${apiPort}/api/v1`,
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
