import { describe, expect, it } from "vitest";
import { innsIn } from "./inn";

describe("innsIn", () => {
  it.each(["7707083893", "500100732259"])("accepts the INN %s with a valid checksum", (inn) => {
    expect(innsIn(`ИНН ${inn}, КПП 773601001`)).toEqual([inn]);
  });

  it("rejects an INN with a wrong checksum", () => {
    expect(innsIn("ИНН 7707083894")).toEqual([]);
  });

  it("rejects the region code 00 even with a valid checksum", () => {
    expect(innsIn("ИНН 0012345673")).toEqual([]);
  });

  it.each(["77070838931", "id7707083893", "7707083893_x", "a1b7707083893"])(
    "does not take the INN out of the longer token %s",
    (token) => {
      expect(innsIn(`номер ${token} в тексте`)).toEqual([]);
    },
  );

  it("finds every INN in the text in order", () => {
    expect(innsIn("ИНН:7707083893; учредитель 500100732259")).toEqual(["7707083893", "500100732259"]);
  });
});
