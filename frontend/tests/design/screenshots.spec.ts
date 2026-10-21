import { expect, test } from "@playwright/test";
import path from "node:path";

const OUTPUT = path.join(__dirname, "..", "..", "..", "docs", "design");
const VIEWPORT = { width: 1600, height: 1000 };

test.use({ viewport: VIEWPORT });

test("dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Что важно для вашего бизнеса" })).toBeVisible();
  await page.screenshot({ path: path.join(OUTPUT, "dashboard.png"), fullPage: true, animations: "disabled" });
});

test.describe("dark theme", () => {
  test.use({ colorScheme: "dark" });

  test("dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Что важно для вашего бизнеса" })).toBeVisible();
    await page.screenshot({ path: path.join(OUTPUT, "dashboard-dark.png"), fullPage: true, animations: "disabled" });
  });
});

test("payment with the panel", async ({ page }) => {
  await page.goto("/payments/new");
  await page.getByLabel("Получатель").selectOption("cp_logistics_spb");
  await page.getByLabel("Сумма, ₽").fill("1500000");
  await page.getByRole("heading", { name: "Платёж контрагенту" }).click();
  await expect(page.locator(".insight-card")).toBeVisible();
  await page.screenshot({ path: path.join(OUTPUT, "payment.png"), fullPage: true, animations: "disabled" });
});

test("profile", async ({ page }) => {
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Профиль компании" })).toBeVisible();
  await page.screenshot({ path: path.join(OUTPUT, "profile.png"), fullPage: true, animations: "disabled" });
});

test("trace", async ({ page }) => {
  await page.goto("/trace/trace-mock-1");
  await page.getByText("План", { exact: true }).click();
  await page.screenshot({ path: path.join(OUTPUT, "trace.png"), fullPage: true, animations: "disabled" });
});

for (const width of [400, 320]) {
  test(`panel ${width}px`, async ({ page }) => {
    await page.goto("/showcase");
    const frame = page.locator(`[data-width="${width}"]`);
    await expect(frame.locator(".insight-card")).toBeVisible();
    await frame.screenshot({ path: path.join(OUTPUT, `panel-${width}.png`), animations: "disabled" });
  });
}
