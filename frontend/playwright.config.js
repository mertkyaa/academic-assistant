import { defineConfig, devices } from "@playwright/test";

// E2E tests run against the live Railway deployment (single-service: API + React).
// The pipeline (paper search + 3 sequential Claude agents) is slow, so timeouts are generous.
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "https://academic-assistant-production-35e4.up.railway.app",
    headless: true,
    trace: "on-first-retry",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
