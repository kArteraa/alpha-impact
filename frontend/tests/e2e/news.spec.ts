import { expect, test } from "@playwright/test";
import { DEMO_NEWS, DEMO_NEWS_URL, pasteNews } from "../support/news";
import { CARD_TIMEOUT_MS } from "../support/panel";
import { logIn } from "../support/session";

test("pasted news from the main screen: card with sources and its trace", async ({ page }) => {
  test.setTimeout(2 * CARD_TIMEOUT_MS);
  await logIn(page);
  await page.getByRole("button", { name: "Всё верно" }).click();

  await page.getByRole("link", { name: "Вставить новость" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Живая новость" })).toBeVisible();
  await pasteNews(page, DEMO_NEWS, DEMO_NEWS_URL);

  const panel = page.locator(".insight-panel");
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.locator(".insight-sources li").first()).toBeVisible();

  await panel.getByRole("link", { name: "Как получен вывод" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Как получен вывод" })).toBeVisible();
  await expect(page.getByText("Вставленная новость", { exact: false }).first()).toBeVisible();
});
