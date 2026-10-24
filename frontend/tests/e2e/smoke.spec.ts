import { expect, test } from "@playwright/test";

test("api answers on /health and the application opens", async ({ page, request }) => {
  const health = await request.get("http://localhost:8000/health");
  expect(health.ok()).toBeTruthy();
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Вход" })).toBeVisible();
});
