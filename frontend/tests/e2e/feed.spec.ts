import { expect, type Page, test } from "@playwright/test";
import { CARD_TIMEOUT_MS, chooseOption, feedWidget, waitForFeed } from "../support/panel";
import { enter } from "../support/session";

async function feedHeadlines(page: Page) {
  await waitForFeed(page);
  return feedWidget(page).getByRole("heading", { level: 3 }).allTextContents();
}

async function headlinesOf(page: Page, userId: string) {
  await enter(page, userId);
  return feedHeadlines(page);
}

test("feed differs between companies on one screen and between seed users", async ({ page }) => {
  test.setTimeout(4 * CARD_TIMEOUT_MS);
  const wholesale = await headlinesOf(page, "user_cfo_wholesale");
  expect(wholesale.length).toBeGreaterThanOrEqual(1);
  expect(wholesale.length).toBeLessThanOrEqual(3);

  await chooseOption(page, "Компания", /СтройЛизинг/);
  const construction = await feedHeadlines(page);
  expect(construction).not.toEqual(wholesale);

  await feedWidget(page).getByRole("heading", { level: 3 }).first().getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: "Событие" })).toBeVisible();
  await expect(page.locator(".insight-card")).toHaveCount(1);

  const autodealer = await headlinesOf(page, "user_cfo_autodealer");
  expect(autodealer).not.toEqual(wholesale);
});
