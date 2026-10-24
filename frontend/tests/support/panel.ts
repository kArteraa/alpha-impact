import { expect, type Locator, type Page } from "@playwright/test";

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

export function feedWidget(page: Page) {
  return page.getByRole("region", { name: "Что изменилось вокруг ваших операций" });
}

export async function feedHeadlines(page: Page) {
  await waitForFeed(page);
  return feedWidget(page).getByRole("heading", { level: 3 }).allTextContents();
}

export async function waitForCard(panel: Locator) {
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });
  await expect(panel).toHaveAttribute("aria-busy", "false", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.locator(".insight-sources li").first()).toBeVisible();
}
