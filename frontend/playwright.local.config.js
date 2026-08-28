import { defineConfig, devices } from "@playwright/test";

// Comprehensive E2E suite run against LOCAL servers:
//   - backend (uvicorn) on :8000 with rate limiting disabled (RATE_LIMIT_ENABLED=false)
//   - frontend (vite dev) on :5173, which points at the local backend via .env
//
// This isolates the negative / validation / auth-heavy tests from production's
// rate limits and lets them register freely. It still uses the shared Railway DB,
// so test accounts are created there — clean them up afterwards (e2e-% emails).
export default defineConfig({
  testDir: "./e2e-local",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:5173",
    headless: true,
    trace: "on-first-retry",
  },
  webServer: [
    {
      command:
        "cd .. && ./venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: true,
      timeout: 60_000,
      env: { RATE_LIMIT_ENABLED: "false" },
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: true,
      timeout: 60_000,
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
