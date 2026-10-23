import { expect, type Page, test } from "@playwright/test";
import { logIn } from "../support/session";

const CARD_TIMEOUT_MS = 60_000;

async function expectRateCard(page: Page) {
  const panel = page.locator(".insight-panel");
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.getByLabel(/^Банк — источник: /).first()).toBeVisible();
  await expect(panel.getByRole("region", { name: "Расчёт" }).first()).toBeVisible();
}

test("deposit and a new tranche show the bank view on the rate with a calculation", async ({ page }) => {
  test.setTimeout(3 * CARD_TIMEOUT_MS);
  await logIn(page);

  await page.getByRole("link", { name: "Депозиты" }).click();
  await page.getByLabel("Сумма, ₽").fill("50000000");
  await expect(page.getByRole("radio", { name: "6 мес." })).toBeChecked();
  await expectRateCard(page);

  await page.getByRole("link", { name: "Кредиты" }).click();
  await page.getByRole("button", { name: "Новый транш" }).click();
  await page.getByRole("combobox", { name: "Продукт" }).click();
  await page.getByRole("option", { name: /Кредитная линия/ }).click();
  await page.getByLabel("Сумма, ₽").fill("50000000");
  await expectRateCard(page);
});
