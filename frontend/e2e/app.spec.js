import { test, expect } from "@playwright/test";

// End-to-end tests against the live Railway deployment.
// Search is open (no login), so these tests just drive the public search + export.
// The synthesis test uses the cached "transformer architecture" topic, so it is
// free (no Claude pipeline run) as long as that entry is warm in the cache.

test.describe("Academic Paper Assistant — live E2E", () => {
  test("API health and static assets are served from the single service", async ({ request }) => {
    const health = await request.get("/api/health");
    expect(health.ok()).toBeTruthy();
    expect((await health.json()).status).toBe("ok");

    // Root-level static file must be the real SVG, not the SPA index.html fallback.
    const favicon = await request.get("/favicon.svg");
    expect(favicon.ok()).toBeTruthy();
    expect(favicon.headers()["content-type"]).toContain("image/svg");
  });

  test("landing page shows the search UI directly (no login required)", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Academic Paper Assistant" })).toBeVisible();
    await expect(page.getByPlaceholder("Enter a research topic...")).toBeVisible();
    await expect(page.getByRole("button", { name: "Search" })).toBeVisible();

    // No auth gate anymore.
    await expect(page.getByRole("heading", { name: "Welcome Back" })).toHaveCount(0);
  });

  test("search returns a synthesis and exports as Markdown + PDF", async ({ page, context }) => {
    test.setTimeout(120_000);
    await context.addInitScript(() => { window.print = () => {}; });

    await page.goto("/");
    await page.getByPlaceholder("Enter a research topic...").fill("transformer architecture");
    await page.getByRole("button", { name: "Search" }).click();
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
