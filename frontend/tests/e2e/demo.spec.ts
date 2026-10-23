import { expect, type Locator, type Page, test } from "@playwright/test";
import { pasteDemoNews } from "../support/news";
import { CARD_TIMEOUT_MS, chooseOption, feedWidget, pay, waitForFeed } from "../support/panel";
import { chooseRole, enter, logIn, logInAgain } from "../support/session";

const CARRIER = "ООО «Северо-Западная логистика»";
const DEMO_PAYMENT = "4500000";
const DEMO_DEPOSIT = "50000000";

function panelOf(page: Page) {
  return page.locator(".insight-panel");
}

async function headlines(page: Page) {
  await waitForFeed(page);
  return feedWidget(page).getByRole("heading", { level: 3 }).allTextContents();
}

async function term(page: Page, label: string) {
  await page.getByRole("radiogroup", { name: "Срок" }).getByText(label, { exact: true }).click();
  await expect(page.getByRole("radio", { name: label })).toBeChecked();
}

async function answered(page: Page, act: () => Promise<void>) {
  const response = page.waitForResponse((reply) => reply.url().endsWith("/api/interpret"), { timeout: CARD_TIMEOUT_MS });
  await act();
  expect((await response).ok()).toBeTruthy();
}

async function expectCard(panel: Locator) {
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });
  await expect(panel).toHaveAttribute("aria-busy", "false", { timeout: CARD_TIMEOUT_MS });
  await expect(panel.locator(".insight-sources li").first()).toBeVisible();
}

async function expectBankCard(panel: Locator) {
  await expectCard(panel);
  await expect(panel.getByLabel(/^Банк — источник: /).first()).toBeVisible();
}

test("demo scenario: profile, feed, payment, silence, deposit, role, pasted news, trace", async ({ page }) => {
  test.setTimeout(12 * CARD_TIMEOUT_MS);
  const panel = panelOf(page);

  await logIn(page);
  await expect(page.getByRole("listitem", { name: "Отрасль" })).toBeVisible();
  await page.getByRole("button", { name: "Всё верно" }).click();

  const wholesale = await headlines(page);
  expect(wholesale.length).toBeGreaterThanOrEqual(1);
  await feedWidget(page).getByRole("link", { name: "Все события" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Все события" })).toBeVisible();
  await page.getByRole("link", { name: "Главная" }).click();
  await chooseOption(page, "Компания", /СтройЛизинг/);
  expect(await headlines(page)).not.toEqual(wholesale);
  await chooseOption(page, "Компания", /Северный опт/);

  await page.getByRole("link", { name: "Платежи" }).click();
  await pay(page, CARRIER, DEMO_PAYMENT);
  await expectBankCard(panel);
  await expect(panel).toHaveAttribute("data-role", "cfo");

  await enter(page, "user_cfo_nocard");
  await expect(feedWidget(page).getByText("Пока ничего важного для вашего бизнеса.")).toBeVisible({ timeout: CARD_TIMEOUT_MS });

  await logInAgain(page);
  await page.getByRole("link", { name: "Депозиты" }).click();
  await page.getByLabel("Сумма, ₽").fill(DEMO_DEPOSIT);
  await answered(page, () => term(page, "3 мес."));
  await expectBankCard(panel);
  await expect(panel.getByRole("region", { name: "Расчёт" }).first()).toBeVisible();
  await answered(page, () => term(page, "6 мес."));
  await expectBankCard(panel);

  await chooseRole(page, "Казначей");
  await page.getByRole("link", { name: "Платежи" }).click();
  await pay(page, CARRIER, DEMO_PAYMENT);
  await expectCard(panel);
  await expect(panel).toHaveAttribute("data-role", "treasurer");

  await chooseRole(page, "Финансовый директор");
  await page.getByRole("link", { name: "Главная" }).click();
  await page.getByRole("link", { name: "Вставить новость" }).click();
  await pasteDemoNews(page);
  await expectCard(panel);

  await panel.getByRole("link", { name: "Как получен вывод" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Как получен вывод" })).toBeVisible();
  const steps = page.getByRole("region", { name: "Шаги" });
  for (const name of ["Разметка вставленной новости", "План агента", "Черновик карточки", "Критик, круг 1"]) {
    await expect(steps.getByText(name, { exact: true }).first()).toBeVisible();
  }
});
