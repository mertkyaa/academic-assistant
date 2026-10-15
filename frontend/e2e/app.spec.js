import { test, expect } from "@playwright/test";
import { PROD_URL } from "../playwright.config.js";

// Page tests run against a locally built copy of the frontend (see
// playwright.config.js), so they verify the commit being pushed rather than
// whatever is currently deployed. Tests that need the real backend hit
// PROD_URL directly, and assert only on things that do not change between
// deploys — so they do not race a deploy either.

test.describe("Academic Research Assistant — E2E", () => {
  test("API health and static assets are served from the single service", async ({ request }) => {
    const health = await request.get(`${PROD_URL}/api/health`);
    expect(health.ok()).toBeTruthy();
    expect((await health.json()).status).toBe("ok");

    // Root-level static file must be the real SVG, not the SPA index.html fallback.
    const favicon = await request.get(`${PROD_URL}/favicon.svg`);
    expect(favicon.ok()).toBeTruthy();
    expect(favicon.headers()["content-type"]).toContain("image/svg");

    // Unknown API paths must 404 rather than quietly returning the SPA shell.
    const unknown = await request.get(`${PROD_URL}/api/not-a-real-endpoint`);
    expect(unknown.status()).toBe(404);
  });

  test("search is open: no account endpoints and no login gate", async ({ request }) => {
    // Accounts were removed; these must be gone in production.
    for (const path of ["/api/me", "/api/history", "/api/register"]) {
      const res = await request.get(`${PROD_URL}${path}`);
      expect(res.status(), `${path} should be gone`).toBe(404);
    }

    // The pipeline is expensive, so the API must reject a topic that is too
    // short instead of running it.
    const tooShort = await request.post(`${PROD_URL}/api/search`, { data: { topic: "a" } });
    expect(tooShort.status()).toBe(422);
  });

  test("landing page shows the search UI directly", async ({ page }) => {
    await page.goto("/");

    // Assert on structure and roles rather than exact copy, so renaming the
    // product does not break the suite.
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.getByRole("textbox")).toBeVisible();
    await expect(page.getByRole("button", { name: /search/i })).toBeVisible();

    // The page must have a real title, not the Vite scaffold's package name.
    await expect(page).toHaveTitle(/assistant/i);

    // No auth gate: nothing asking the visitor to sign in or register.
    await expect(page.getByRole("button", { name: /sign in|sign up|log in/i })).toHaveCount(0);
    await expect(page.getByPlaceholder(/password/i)).toHaveCount(0);
  });

  test("search returns a synthesis and exports as Markdown + PDF", async ({ page, context }) => {
    test.setTimeout(120_000);
    await context.addInitScript(() => { window.print = () => {}; });

    await page.goto("/");
    await page.getByRole("textbox").fill("transformer architecture");
    await page.getByRole("button", { name: /search/i }).click();
    await expect(page.getByText(/\d+ papers/)).toBeVisible({ timeout: 90_000 });

    // Markdown download
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Markdown/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.md$/);

    // PDF opens a print-ready popup
    const popupPromise = context.waitForEvent("page");
    await page.getByRole("button", { name: /PDF/ }).click();
    const popup = await popupPromise;
    await expect(popup.locator("h1.title")).toBeVisible({ timeout: 10_000 });
    await popup.close();
  });
});
