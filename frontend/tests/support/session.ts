import { expect, type Page } from "@playwright/test";

const PROFILE_HEADING = "Профиль компании";

async function submitLogin(page: Page, userId: string) {
  await page.goto("/login");
  await page.getByLabel("Тестовый пользователь").fill(userId);
  await page.getByRole("button", { name: "Войти" }).click();
}

async function pickRole(page: Page, role: string) {
  await page.getByLabel(role).check();
  await page.getByRole("button", { name: "Продолжить" }).click();
  await expect(page.getByRole("heading", { name: PROFILE_HEADING })).toBeVisible();
}

export async function logIn(page: Page, userId = "user_cfo_wholesale", role = "Финансовый директор") {
  await submitLogin(page, userId);
  await pickRole(page, role);
}

export async function enter(page: Page, userId = "user_cfo_wholesale") {
  await logIn(page, userId);
  await page.getByRole("button", { name: "Всё верно" }).click();
}

export async function logInWithSavedRole(page: Page, userId = "user_cfo_wholesale") {
  await submitLogin(page, userId);
  await expect(page.getByRole("heading", { name: PROFILE_HEADING })).toBeVisible();
}

export async function chooseRole(page: Page, role: string) {
  await page.goto("/role");
  await pickRole(page, role);
}
