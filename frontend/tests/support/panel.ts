import { expect, type Page } from "@playwright/test";

export const CARD_TIMEOUT_MS = 60_000;

export async function chooseOption(page: Page, label: string, option: string | RegExp) {
  await page.getByRole("combobox", { name: label }).click();
  await page.getByRole("option", { name: option }).click();
}

export async function pay(page: Page, recipient: string | RegExp, amount: string) {
  await chooseOption(page, "Получатель", recipient);
  await page.getByLabel("Сумма, ₽").fill(amount);
}

export async function askTranche(page: Page, product: RegExp, amount: string) {
  await page.getByRole("button", { name: "Новый транш" }).click();
  await chooseOption(page, "Продукт", product);
  await page.getByLabel("Сумма, ₽").fill(amount);
}

export async function waitForFeed(page: Page) {
  await expect(page.locator(".event").first()).toBeVisible({ timeout: CARD_TIMEOUT_MS });
}
