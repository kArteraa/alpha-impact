import { expect, type Page, test } from "@playwright/test";
import { CARD_TIMEOUT_MS, chooseOption, waitForFeed } from "../support/panel";
import { logIn } from "../support/session";

function widget(page: Page) {
  return page.getByRole("region", { name: "Что изменилось вокруг ваших операций" });
}

async function feedHeadlines(page: Page) {
  await waitForFeed(page);
  return widget(page).getByRole("heading", { level: 3 }).allTextContents();
}

async function enter(page: Page, userId: string) {
  await logIn(page, userId);
  await page.getByRole("button", { name: "Всё верно" }).click();
  return feedHeadlines(page);
}

test("feed differs between companies on one screen and between seed users", async ({ page }) => {
  test.setTimeout(4 * CARD_TIMEOUT_MS);
  const wholesale = await enter(page, "user_cfo_wholesale");
  expect(wholesale.length).toBeGreaterThanOrEqual(1);
  expect(wholesale.length).toBeLessThanOrEqual(3);

  await chooseOption(page, "Компания", /СтройЛизинг/);
  const construction = await feedHeadlines(page);
  expect(construction).not.toEqual(wholesale);

  await widget(page).getByRole("heading", { level: 3 }).first().getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: "Событие" })).toBeVisible();
  await expect(page.locator(".insight-card")).toHaveCount(1);

  const autodealer = await enter(page, "user_cfo_autodealer");
  expect(autodealer).not.toEqual(wholesale);
});
