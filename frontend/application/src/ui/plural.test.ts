import { describe, expect, it } from "vitest";
import { plural } from "./plural";

const DAYS = { one: "день", few: "дня", many: "дней" };

describe("plural", () => {
  it.each([
    [1, "1 день"],
    [3, "3 дня"],
    [5, "5 дней"],
    [11, "11 дней"],
    [21, "21 день"],
    [70, "70 дней"],
  ])("names %i", (count, text) => {
    expect(plural(count, DAYS)).toBe(text);
  });
});
