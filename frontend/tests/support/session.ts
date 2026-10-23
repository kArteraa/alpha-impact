import { expect, type Page } from "@playwright/test";

export async function logIn(page: Page, userId = "user_cfo_wholesale", role = "Финансовый директор") {
  await page.goto("/login");
  await page.getByLabel("Тестовый пользователь").fill(userId);
  await page.getByRole("button", { name: "Войти" }).click();
  await page.getByLabel(role).check();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByRole("heading", { name: "Профиль компании" })).toBeVisible();
}
