import { test, expect } from "@playwright/test";

// Comprehensive auth/profile E2E against the LOCAL stack (rate limiting disabled).
// Focuses on the paths the live "happy journey" test does NOT cover: client-side
// validation, server-side rejections, the login flow, wrong-password handling,
// session persistence, profile edge cases, and negative search.
//
// These do not call the Claude pipeline, so they are free. Test accounts use the
// "e2e-" email prefix and are cleaned up by a script after the run.

const PASSWORD = "TestPass123!";

let seq = 0;
function creds(tag) {
  seq += 1;
  const s = `${Date.now()}${seq}`;
  return {
    email: `e2e-${tag}${s}@example.com`,
    username: `e2e${tag}${s}`.slice(0, 30),
    password: PASSWORD,
  };
}

async function gotoRegister(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Sign Up" }).click();
  await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();
}

async function register(page, c) {
  await gotoRegister(page);
  await page.getByPlaceholder("Username").fill(c.username);
  await page.getByPlaceholder("Email").fill(c.email);
  await page.getByPlaceholder("Password").fill(c.password);
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByRole("button", { name: "Logout" })).toBeVisible();
}

async function login(page, email, password) {
  // Auth modal is in login mode by default (and after logout).
  await page.getByPlaceholder("Email").fill(email);
  await page.getByPlaceholder("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
}

test.describe("Comprehensive auth & profile (local)", () => {
  test("client-side validation shows friendly, specific messages", async ({ page }) => {
    await gotoRegister(page);

    // Invalid email
    await page.getByPlaceholder("Username").fill("validuser");
    await page.getByPlaceholder("Email").fill("notanemail");
    await page.getByPlaceholder("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText("Please enter a valid email address.")).toBeVisible();

    // Short username
    await page.getByPlaceholder("Email").fill("ok@example.com");
    await page.getByPlaceholder("Username").fill("ab");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText(/Username must be 3-30 characters/)).toBeVisible();

    // Short password
    await page.getByPlaceholder("Username").fill("validuser");
    await page.getByPlaceholder("Password").fill("short");
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText("Password must be at least 8 characters.")).toBeVisible();

    // Never left the modal / never logged in
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeVisible();
  });

  test("register logs the user in and shows the username", async ({ page }) => {
    const c = creds("reg");
    await register(page, c);
    await expect(page.getByRole("heading", { name: "Create Account" })).toBeHidden();
    await expect(page.getByText(c.username)).toBeVisible();
  });

  test("server rejects duplicate email and duplicate username with clear text", async ({ page }) => {
    const c = creds("dup");
    await register(page, c);
    await page.getByRole("button", { name: "Logout" }).click();

    await page.getByRole("button", { name: "Sign Up" }).click();
    // Duplicate email (fresh username)
    await page.getByPlaceholder("Username").fill(`fresh${Date.now()}`.slice(0, 30));
    await page.getByPlaceholder("Email").fill(c.email);
    await page.getByPlaceholder("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText("Email already registered")).toBeVisible();

    // Duplicate username (fresh email)
    await page.getByPlaceholder("Email").fill(`fresh${Date.now()}@example.com`);
    await page.getByPlaceholder("Username").fill(c.username);
    await page.getByRole("button", { name: "Create Account" }).click();
    await expect(page.getByText("Username already taken")).toBeVisible();
  });

  test("returning user: wrong password rejected, correct password logs in", async ({ page }) => {
    const c = creds("login");
    await register(page, c);
    await page.getByRole("button", { name: "Logout" }).click();

    // Wrong password
    await login(page, c.email, "WrongPass999!");
    await expect(page.getByText("Invalid email or password")).toBeVisible();

    // Correct password
    await page.getByPlaceholder("Password").fill(c.password);
    await page.getByRole("button", { name: "Sign In" }).click();
    await expect(page.getByText(c.username)).toBeVisible();
  });

  test("session persists across a page reload", async ({ page }) => {
    const c = creds("sess");
    await register(page, c);
    await page.reload();
    await expect(page.getByRole("button", { name: "Logout" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Welcome Back" })).toBeHidden();
  });

  test("profile: wrong current password rejected; change works and new password logs in", async ({ page }) => {
    const c = creds("pw");
    await register(page, c);

    await page.getByRole("button", { name: "Profile" }).click();
    await expect(page.getByRole("heading", { name: "Profile" })).toBeVisible();
    await expect(page.getByText(c.email)).toBeVisible();

    // Wrong current password
    await page.getByPlaceholder("Current password").fill("WrongNow123!");
    await page.getByPlaceholder("New password (min 8 chars)").fill("BrandNew123!");
    await page.getByRole("button", { name: "Update Password" }).click();
    await expect(page.getByText("Current password is incorrect")).toBeVisible();

    // Correct change
    const newPassword = "Changed123!";
    await page.getByPlaceholder("Current password").fill(c.password);
    await page.getByPlaceholder("New password (min 8 chars)").fill(newPassword);
    await page.getByRole("button", { name: "Update Password" }).click();
    await expect(page.getByText("Password changed.")).toBeVisible();

    // Close profile, log out, log in with the NEW password
    await page.getByRole("button", { name: "✕" }).click();
    await page.getByRole("button", { name: "Logout" }).click();
    await login(page, c.email, newPassword);
    await expect(page.getByText(c.username)).toBeVisible();
  });

  test("profile: updating to an already-taken username is rejected", async ({ page }) => {
    const a = creds("ua");
    const b = creds("ub");
    await register(page, a);
    await page.getByRole("button", { name: "Logout" }).click();
    await register(page, b);

    // Logged in as b; try to take a's username
    await page.getByRole("button", { name: "Profile" }).click();
    await page.getByPlaceholder("Username").fill(a.username);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Username already taken")).toBeVisible();
  });

  test("search button is disabled for a too-short query and enabled otherwise", async ({ page }) => {
    const c = creds("srch");
    await register(page, c);

    const searchBtn = page.getByRole("button", { name: "Search" });
    const input = page.getByPlaceholder("Enter a research topic...");

    // Too short (< 5 chars) → the guard disables the button.
    await input.fill("abc");
    await expect(searchBtn).toBeDisabled();

    // Valid length → button becomes enabled (we don't submit, to avoid a pipeline run).
    await input.fill("transformer architecture");
    await expect(searchBtn).toBeEnabled();

    // No synthesis rendered without submitting.
    await expect(page.getByText(/\d+ papers/)).toHaveCount(0);
  });
});
