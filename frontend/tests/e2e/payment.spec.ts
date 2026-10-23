import { expect, test } from "@playwright/test";
import { CARD_TIMEOUT_MS, pay } from "../support/panel";
import { logIn } from "../support/session";

test("login, profile, carrier card with sources, silent stationery payment", async ({ page }) => {
  test.setTimeout(3 * CARD_TIMEOUT_MS);
  await logIn(page);

  await expect(page.getByRole("listitem", { name: "Отрасль" })).toBeVisible();
  await page.getByRole("button", { name: "Всё верно" }).click();
  await expect(page.getByRole("heading", { name: "Что изменилось вокруг ваших операций" })).toBeVisible();

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
