import type { Page } from "@playwright/test";

export const DEMO_NEWS_URL = "https://demo.example/cbr-key-rate";

export const DEMO_NEWS = [
  "Банк России сохранил ключевую ставку на уровне 14% годовых",
  "Совет директоров Банка России сохранил ключевую ставку на уровне 14% годовых. Регулятор отметил, что инфляция замедляется, но остаётся выше цели, и допустил снижение ставки в начале следующего года. Кредиты для бизнеса остаются дорогими, банки сохраняют высокие ставки по депозитам.",
].join("\n");

export async function pasteDemoNews(page: Page) {
  await page.getByLabel("Ссылка на источник").fill(DEMO_NEWS_URL);
  await page.getByLabel("Текст новости").fill(DEMO_NEWS);
  await page.getByRole("button", { name: "Разобрать новость" }).click();
}
