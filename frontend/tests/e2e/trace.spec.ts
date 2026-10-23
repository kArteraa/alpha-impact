import { expect, test } from "@playwright/test";
import { CARD_TIMEOUT_MS, pay } from "../support/panel";
import { logIn } from "../support/session";

test("carrier card: feedback, trace from top to bottom, sources lead to the article and the report page", async ({
  page,
}) => {
  test.setTimeout(2 * CARD_TIMEOUT_MS);
  await logIn(page);

  await page.goto("/payments/new");
  await pay(page, /Северо-Западная логистика/, "1500000");
  const panel = page.locator(".insight-panel");
  await expect(panel).toHaveAttribute("data-state", "cards", { timeout: CARD_TIMEOUT_MS });

  const useful = panel.getByRole("button", { name: "Полезно" }).first();
  const feedback = page.waitForResponse((response) => response.url().endsWith("/api/feedback"));
  await useful.click();
  expect((await feedback).status()).toBe(204);
  await expect(useful).toHaveAttribute("aria-pressed", "true");

  await panel.getByRole("link", { name: "Как получен вывод" }).first().click();
  await expect(page.getByRole("heading", { level: 1, name: "Как получен вывод" })).toBeVisible();
  const steps = page.getByRole("region", { name: "Шаги" });
  for (const name of ["Профиль компании", "Отбор новостей", "План агента", "Черновик карточки", "Критик, круг 1"]) {
    await expect(steps.getByText(name, { exact: true }).first()).toBeVisible();
  }

  const result = page.getByRole("region", { name: "Итог" });
  const news = result.locator('.insight-sources a[href^="http"]').first();
  await expect(news).toHaveAttribute("target", "_blank");
  const report = result.locator('.insight-sources a[href^="/api/reports/"]').first();
  const href = await report.getAttribute("href");
  expect(href).toMatch(/\.pdf(#page=\d+)?$/);
  const pdf = await page.request.get(href ?? "", { headers: { Range: "bytes=0-0" } });
  expect(pdf.status()).toBe(206);
  expect(pdf.headers()["content-type"]).toBe("application/pdf");
});
