import { describe, expect, it } from "vitest";
import { matchIndex, moveIndex } from "./listbox";

const LABELS = ["ООО «Северо-Западная логистика»", "ООО «Канцмир»", "АО «СтройЛизинг»", "Сбербанк"];

describe("moveIndex", () => {
  it.each([
    ["ArrowDown", 0, 1],
    ["ArrowDown", 3, 3],
    ["ArrowDown", -1, 0],
    ["ArrowUp", 2, 1],
    ["ArrowUp", 0, 0],
    ["ArrowUp", -1, 0],
    ["Home", 2, 0],
    ["End", 0, 3],
    ["PageDown", 0, 3],
    ["PageUp", 3, 0],
  ])("moves %s from %i to %i in a list of four", (key, from, to) => {
    expect(moveIndex(key, from, LABELS.length)).toBe(to);
  });

  it("ignores keys that do not move", () => {
    expect(moveIndex("Enter", 1, LABELS.length)).toBeNull();
  });
});

describe("matchIndex", () => {
  it("finds a company by its name without the legal form and quotes", () => {
    expect(matchIndex(LABELS, "к", -1)).toBe(1);
    expect(matchIndex(LABELS, "стр", -1)).toBe(2);
  });

  it("finds by the full label too", () => {
    expect(matchIndex(LABELS, "ао", -1)).toBe(2);
  });

  it("cycles through options that start with the same letter", () => {
    expect(matchIndex(LABELS, "с", -1)).toBe(0);
    expect(matchIndex(LABELS, "с", 0)).toBe(2);
    expect(matchIndex(LABELS, "с", 2)).toBe(3);
    expect(matchIndex(LABELS, "с", 3)).toBe(0);
  });

  it("keeps the current option while a longer query still matches it", () => {
    expect(matchIndex(LABELS, "се", 0)).toBe(0);
  });

  it("returns -1 when nothing matches", () => {
    expect(matchIndex(LABELS, "я", 1)).toBe(-1);
  });
});
