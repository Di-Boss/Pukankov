import { defineConfig } from "@playwright/test";
import { randomBytes } from "node:crypto";
import { resolve } from "node:path";
process.env.PUKANKOV_E2E_PASSWORD ||= randomBytes(20).toString("hex");
process.env.DATABASE_URL ||= `sqlite:///${resolve(".test-artifacts", `e2e-${Date.now()}.db`).replaceAll("\\", "/")}`;
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  expect: { timeout: 10000 },
  reporter: "list",
  outputDir: ".test-artifacts/playwright-results",
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    timezoneId: "Europe/Sofia",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: process.env.PUKANKOV_EXTERNAL_SERVERS
    ? undefined
    : [
        {
          command: "python scripts/e2e_server.py",
          url: "http://127.0.0.1:8001/api/v1/health",
          env: { PUBLIC_ORIGIN: "http://127.0.0.1:5174" },
          reuseExistingServer: false,
          timeout: 60000,
        },
        {
          command: "npm run dev -- --port 5174 --strictPort",
          url: "http://127.0.0.1:5174",
          env: { VITE_API_TARGET: "http://127.0.0.1:8001" },
          reuseExistingServer: false,
          timeout: 60000,
        },
      ],
});
