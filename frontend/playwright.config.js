import { defineConfig, devices } from "@playwright/test";

// The deployed API, used only by tests that must talk to the real backend.
export const PROD_URL = "https://academic-assistant-production-35e4.up.railway.app";

// Port for the preview server below. Must stay in ALLOWED_ORIGINS in main.py,
// since the built bundle calls the deployed API cross-origin from here.
const PREVIEW_PORT = 4173;

// Page tests run against a locally built and served copy of the frontend, not
// against the deployment. That is deliberate: when CI tested the live site, any
// change to the UI failed until Railway finished deploying, so every push went
// red for a minute and had to be re-run. Serving the build from this commit
// removes the deploy from the equation entirely — the tests check the code that
// is actually being pushed.
//
// Tests that need the real backend (API health, the live search) target
// PROD_URL explicitly instead.
export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://localhost:${PREVIEW_PORT}`,
    headless: true,
    trace: "on-first-retry",
  },
  webServer: {
    command: `npm run build && npm run preview -- --port ${PREVIEW_PORT} --strictPort`,
    url: `http://localhost:${PREVIEW_PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
