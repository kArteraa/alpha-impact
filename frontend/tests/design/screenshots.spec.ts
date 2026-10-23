import { expect, test } from "@playwright/test";
import path from "node:path";
import { askTranche, CARD_TIMEOUT_MS, pay, waitForFeed } from "../support/panel";
import { logIn } from "../support/session";

const OUTPUT = path.join(__dirname, "..", "..", "..", "docs", "design");
const VIEWPORT = { width: 1600, height: 1000 };

test.use({ viewport: VIEWPORT });

test.beforeEach(async ({ page }) => {
  await logIn(page);
});

test("dashboard", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Что изменилось вокруг ваших операций" })).toBeVisible();
  await waitForFeed(page);
  await page.screenshot({ path: path.join(OUTPUT, "dashboard.png"), fullPage: true, animations: "disabled" });
});

test.describe("dark theme", () => {
  test.use({ colorScheme: "dark" });

  test("dashboard", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Что изменилось вокруг ваших операций" })).toBeVisible();
    await waitForFeed(page);
    await page.screenshot({ path: path.join(OUTPUT, "dashboard-dark.png"), fullPage: true, animations: "disabled" });
  });
});

test("payment with the panel", async ({ page }) => {
  await page.goto("/payments/new");
  await pay(page, /Северо-Западная логистика/, "1500000");
  await page.getByRole("heading", { name: "Платёж контрагенту" }).click();
  await expect(page.locator(".insight-card").first()).toBeVisible({ timeout: CARD_TIMEOUT_MS });
  await page.screenshot({ path: path.join(OUTPUT, "payment.png"), fullPage: true, animations: "disabled" });
});

test("profile", async ({ page }) => {
  await page.goto("/profile");
  await expect(page.getByRole("heading", { name: "Профиль компании" })).toBeVisible();
  await page.screenshot({ path: path.join(OUTPUT, "profile.png"), fullPage: true, animations: "disabled" });
});

test("events", async ({ page }) => {
  await page.goto("/events");
  await expect(page.getByRole("heading", { name: "Все события" })).toBeVisible();
  await waitForFeed(page);
  await page.screenshot({ path: path.join(OUTPUT, "events.png"), fullPage: true, animations: "disabled" });
});

test("deposit", async ({ page }) => {
  await page.goto("/deposits/new");
  await page.getByLabel("Сумма, ₽").fill("10000000");
  await page.getByRole("heading", { name: "Разместить средства" }).click();
  await expect(page.locator(".insight-card").first()).toBeVisible({ timeout: CARD_TIMEOUT_MS });
  await page.screenshot({ path: path.join(OUTPUT, "deposit.png"), fullPage: true, animations: "disabled" });
});

test("loans", async ({ page }) => {
  await page.goto("/loans");
  await expect(page.getByRole("table", { name: "Кредитный портфель" })).toBeVisible();
  await askTranche(page, /Кредитная линия/, "50000000");
  await page.getByRole("heading", { name: "Новый транш" }).click();
  await expect(page.locator(".insight-card").first()).toBeVisible({ timeout: CARD_TIMEOUT_MS });
  await page.screenshot({ path: path.join(OUTPUT, "loans.png"), fullPage: true, animations: "disabled" });
});

test("login", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Вход" })).toBeVisible();
  await page.screenshot({ path: path.join(OUTPUT, "login.png"), fullPage: true, animations: "disabled" });
});

test("trace", async ({ page }) => {
  await page.goto("/payments/new");
  await pay(page, /Северо-Западная логистика/, "1500000");
  await expect(page.locator(".insight-card").first()).toBeVisible({ timeout: CARD_TIMEOUT_MS });
  await page.getByRole("link", { name: "Как получен вывод" }).first().click();
  await page.getByText("План агента", { exact: true }).first().click();
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
