import { expect, type Page, test } from "@playwright/test";
import { logIn } from "../support/session";

const CARD_TIMEOUT_MS = 60_000;

async function pay(page: Page, recipient: string, amount: string) {
  await page.getByRole("combobox", { name: "Получатель" }).click();
  await page.getByRole("option", { name: recipient }).click();
  await page.getByLabel("Сумма, ₽").fill(amount);
}

test("login, profile, carrier card with sources, silent stationery payment", async ({ page }) => {
  test.setTimeout(3 * CARD_TIMEOUT_MS);
  await logIn(page);

  await expect(page.getByRole("listitem", { name: "Отрасль" })).toBeVisible();
  await page.getByRole("button", { name: "Всё верно" }).click();
  await expect(page.getByRole("heading", { name: "Что важно для вашего бизнеса" })).toBeVisible();

  await page.getByRole("link", { name: "Платежи" }).click();
  await pay(page, "ООО «Северо-Западная логистика»", "1500000");
  const panel = page.locator(".insight-panel");
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.locator(".insight-card").first()).toBeVisible();
  await expect(panel.locator(".insight-sources li").first()).toBeVisible();

  await pay(page, "ООО «Канцмир»", "20000");
  await expect(panel).toHaveAttribute("data-state", "silent", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.getByRole("status")).toHaveText("Ничего важного по этому действию");
});
