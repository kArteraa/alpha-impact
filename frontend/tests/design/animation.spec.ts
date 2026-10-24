import { type Page, test } from "@playwright/test";
import { rmSync } from "node:fs";
import path from "node:path";
import { CARD_TIMEOUT_MS } from "../support/panel";
import { logIn } from "../support/session";

const FRAMES = path.join(__dirname, "..", "..", "test-results", "readme-frames");
const ANIMATION_TIMEOUT_MS = 5 * CARD_TIMEOUT_MS;

test.use({ viewport: { width: 1440, height: 980 } });

class Film {
  private index = 0;

  constructor(private readonly page: Page) {}

  async still(frames: number) {
    for (let frame = 0; frame < frames; frame += 1) {
      await this.page.screenshot({ path: path.join(FRAMES, `f${String(this.index).padStart(4, "0")}.png`) });
      this.index += 1;
    }
  }

  async roll(ms: number) {
    const until = Date.now() + ms;
    while (Date.now() < until) {
      await this.still(1);
    }
  }
}

test("frames of the README animation", async ({ page }) => {
  test.setTimeout(ANIMATION_TIMEOUT_MS);
  rmSync(FRAMES, { recursive: true, force: true });
  const film = new Film(page);
  await logIn(page);
  await film.still(6);
  await page.getByRole("button", { name: "Всё верно" }).click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await film.roll(1500);
  await page.locator(".event").first().waitFor({ timeout: CARD_TIMEOUT_MS });
  await film.roll(1200);
  await film.still(10);
  const tiles = page.locator(".quick-action");
  for (let tile = 0; tile < (await tiles.count()); tile += 1) {
    await tiles.nth(tile).hover();
    await film.still(5);
  }
  await page.getByRole("link", { name: "Вставить новость" }).hover();
  await film.still(5);
  const headline = page.locator(".event").first().getByRole("link").first();
  await headline.hover();
  await film.still(4);
  await headline.click();
  await page.locator(".insight-card").first().waitFor();
  await film.roll(800);
  await film.still(12);
  await page.mouse.wheel(0, 500);
  await film.roll(600);
  await film.still(10);
  await page.goBack();
  await page.locator(".event").first().waitFor();
  await page.evaluate(() => window.scrollTo(0, 0));
  await film.roll(600);
  await film.still(10);
});
