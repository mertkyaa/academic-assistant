import { test, expect } from "@playwright/test";

// End-to-end tests against the live Railway deployment.
// NOTE: the "register + search" test uses a disposable, synthetic account and a
// throwaway password (not a real secret). A fresh unique email is generated per run
// so runs never collide with each other or with existing users.

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

  test("landing page renders behind the auth gate", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Academic Paper Assistant" })).toBeVisible();

    // Auth modal (login mode by default)
    await expect(page.getByRole("heading", { name: "Welcome Back" })).toBeVisible();
    await expect(page.getByPlaceholder("Email")).toBeVisible();
    await expect(page.getByPlaceholder("Password")).toBeVisible();
    await expect(page.getByRole("button", { name: "Sign In" })).toBeVisible();
  });

  test("register a new account, then run a full search", async ({ page }) => {
    test.setTimeout(120_000);
    await page.goto("/");

    // Toggle from login to register mode.
    await page.getByRole("button", { name: "Sign Up" }).click();
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();

    // Disposable synthetic credentials — unique per run.
    const email = `e2e-${Date.now()}@example.com`;
    await page.getByPlaceholder("Email").fill(email);
    await page.getByPlaceholder("Password").fill("TestPass123!");

    // The submit button (not the heading) shares the "Create Account" label.
    await page.getByRole("button", { name: "Create Account" }).click();

    // On success the app stores the token and closes the modal.
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeHidden();

    // Run a real search (search requires >= 5 chars).
    await page.getByPlaceholder("Enter a research topic...").fill("transformer architecture");
    await page.getByRole("button", { name: "Search" }).click();

    // The synthesis card shows an "N papers" badge once the pipeline finishes.
    // Pipeline = paper search + 3 sequential Claude agents, so allow up to 90s.
    await expect(page.getByText(/\d+ papers/)).toBeVisible({ timeout: 90_000 });
  });
});
