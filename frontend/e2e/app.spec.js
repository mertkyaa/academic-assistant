import { test, expect } from "@playwright/test";

// End-to-end tests against the live Railway deployment.
// The full-journey test uses a disposable, synthetic account (unique email +
// username per run) and a throwaway password (not a real secret). It deletes the
// account at the end, so it cleans up after itself.

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

  test("full journey: register, search, export, profile, delete", async ({ page, context }) => {
    test.setTimeout(120_000);

    // Neutralize the printable popup's auto window.print() so it can't block.
    await context.addInitScript(() => {
      window.print = () => {};
    });

    const stamp = Date.now();
    const email = `e2e-${stamp}@example.com`;
    const username = `e2euser${stamp}`;
    const password = "TestPass123!";
    const newPassword = "NewPass456!";

    await page.goto("/");

    // --- Register with a username (M13) ---
    await page.getByRole("button", { name: "Sign Up" }).click();
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();
    await page.getByPlaceholder("Username").fill(username);
    await page.getByPlaceholder("Email").fill(email);
    await page.getByPlaceholder("Password").fill(password);
    // Submit button shares the "Create Account" label with the heading.
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeHidden();

    // Header shows the username once logged in.
    await expect(page.getByText(username)).toBeVisible();

    // --- Search (uses the cached "transformer architecture" result = free) ---
    await page.getByPlaceholder("Enter a research topic...").fill("transformer architecture");
    await page.getByRole("button", { name: "Search" }).click();
    await expect(page.getByText(/\d+ papers/)).toBeVisible({ timeout: 90_000 });

    // --- Export (M12): Markdown download + PDF popup ---
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /Markdown/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.md$/);

    const popupPromise = context.waitForEvent("page");
    await page.getByRole("button", { name: /PDF/ }).click();
    const popup = await popupPromise;
    await expect(popup.locator("h1.title")).toBeVisible({ timeout: 10_000 });
    await popup.close();

    // --- Profile (M13): view, update username, change password ---
    await page.getByRole("button", { name: "Profile" }).click();
    await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();

    const newUsername = `renamed${stamp}`;
    await page.getByPlaceholder("Username").fill(newUsername);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Username updated.")).toBeVisible();

    await page.getByPlaceholder("Current password").fill(password);
    await page.getByPlaceholder("New password (min 8 chars)").fill(newPassword);
    await page.getByRole("button", { name: "Update Password" }).click();
    await expect(page.getByText("Password changed.")).toBeVisible();

    // --- Delete account (cleanup) ---
    await page.getByRole("button", { name: "Delete Account" }).click();
    await page.getByRole("button", { name: "Yes, delete" }).click();
    // Deletion logs the user out: the auth modal returns (mode-agnostic) and the
    // logged-in header controls disappear. The Email input only exists on the auth
    // modal (not the profile modal), so its presence confirms we're back at the gate.
    await expect(page.getByPlaceholder("Email")).toBeVisible();
    await expect(page.getByRole("button", { name: "Logout" })).toBeHidden();
  });
});
