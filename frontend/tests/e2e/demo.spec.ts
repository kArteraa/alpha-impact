import { expect, type Page, type Response, test } from "@playwright/test";
import { pasteDemoNews } from "../support/news";
import { CARD_TIMEOUT_MS, chooseOption, feedHeadlines, feedWidget, pay, waitForCard } from "../support/panel";
import { chooseRole, enter, logIn, logInWithSavedRole } from "../support/session";

const CARRIER = "ООО «Северо-Западная логистика»";
const DEMO_PAYMENT = "4500000";
const DEMO_DEPOSIT = "50000000";
const DEMO_STEPS = 20;

type Asked = (body: { role: string; action_context: Record<string, unknown> }) => boolean;

function section(page: Page, name: string) {
  return page.getByRole("navigation", { name: "Разделы" }).getByRole("link", { name, exact: true });
}

async function answered(page: Page, asked: Asked, act: () => Promise<void>): Promise<Response> {
  const [response] = await Promise.all([
    page.waitForResponse(
      (reply) => reply.url().endsWith("/api/interpret") && asked(reply.request().postDataJSON()),
      { timeout: CARD_TIMEOUT_MS },
    ),
    act(),
  ]);
  expect(response.ok()).toBeTruthy();
  return response;
}

async function term(page: Page, label: string) {
  await page.getByRole("radiogroup", { name: "Срок" }).getByText(label, { exact: true }).click();
  await expect(page.getByRole("radio", { name: label })).toBeChecked();
}

const deposit =
  (days: number): Asked =>
  ({ action_context }) =>
    action_context.type === "deposit" && action_context.term_days === days;

const payment =
  (role: string): Asked =>
  ({ role: asked, action_context }) =>
    asked === role && action_context.type === "payment";

test("demo scenario: profile, feed, payment, silence, deposit, role, pasted news, trace", async ({ page }) => {
  test.setTimeout(DEMO_STEPS * CARD_TIMEOUT_MS);
  const panel = page.locator(".insight-panel");
  const bankBadge = panel.getByLabel(/^Банк — источник: /).first();

  await logIn(page);
  await expect(page.getByRole("listitem", { name: "Отрасль" })).toBeVisible();
  await page.getByRole("button", { name: "Всё верно" }).click();

  const wholesale = await feedHeadlines(page);
  await feedWidget(page).getByRole("link", { name: "Все события" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Все события" })).toBeVisible();
  await section(page, "Главная").click();
  await chooseOption(page, "Компания", /СтройЛизинг/);
  expect(await feedHeadlines(page)).not.toEqual(wholesale);
  await chooseOption(page, "Компания", /Северный опт/);
  await feedHeadlines(page);
  await feedWidget(page).getByRole("heading", { level: 3 }).first().getByRole("link").click();
  await expect(page.getByRole("heading", { level: 1, name: "Событие" })).toBeVisible();
  await expect(page.locator(".insight-card")).toHaveCount(1);

  await section(page, "Платежи").click();
  await answered(page, payment("cfo"), () => pay(page, CARRIER, DEMO_PAYMENT));
  await waitForCard(panel);
  await expect(bankBadge).toBeVisible();

  await enter(page, "user_cfo_nocard");
  await expect(feedWidget(page).getByText("Пока ничего важного для вашего бизнеса.")).toBeVisible({ timeout: CARD_TIMEOUT_MS });

  await logInWithSavedRole(page);
  await section(page, "Депозиты").click();
  await term(page, "3 мес.");
  await answered(page, deposit(90), () => page.getByLabel("Сумма, ₽").fill(DEMO_DEPOSIT));
  await waitForCard(panel);
  await expect(bankBadge).toBeVisible();
  await expect(panel.getByRole("region", { name: "Расчёт" }).first()).toBeVisible();
  await answered(page, deposit(180), () => term(page, "6 мес."));
  await waitForCard(panel);
  await expect(bankBadge).toBeVisible();
  await expect(panel.getByRole("region", { name: "Расчёт" }).first()).toBeVisible();

  await chooseRole(page, "Казначей");
  await section(page, "Платежи").click();
  await answered(page, payment("treasurer"), () => pay(page, CARRIER, DEMO_PAYMENT));
  await waitForCard(panel);

  await chooseRole(page, "Финансовый директор");
  await section(page, "Главная").click();
  await page.getByRole("link", { name: "Вставить новость" }).click();
  await pasteDemoNews(page);
  await waitForCard(panel);

  await panel.getByRole("link", { name: "Как получен вывод" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Как получен вывод" })).toBeVisible();
  const steps = page.getByRole("region", { name: "Шаги" });
  for (const name of ["Разметка вставленной новости", "План агента", "Черновик карточки", "Критик, круг 1"]) {
    await expect(steps.getByText(name, { exact: true }).first()).toBeVisible();
  }
});
