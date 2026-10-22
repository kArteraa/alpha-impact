import { describe, expect, it } from "vitest";
import { areaPath, linePath, linePoints, ratio, shares } from "./scale";

describe("linePoints", () => {
  it("spreads values across the width and flips the y axis", () => {
    expect(linePoints([0, 5, 10], 100, 50, 0)).toEqual([
      [0, 50],
      [50, 25],
      [100, 0],
    ]);
  });

  it("keeps the inset free on every side", () => {
    expect(linePoints([0, 10], 100, 50, 5)).toEqual([
      [5, 45],
      [95, 5],
    ]);
  });

  it("draws a flat series through the middle", () => {
    expect(linePoints([7, 7], 100, 40, 0)).toEqual([
      [0, 20],
      [100, 20],
    ]);
  });
});

describe("paths", () => {
  const points: [number, number][] = [
    [0, 10],
    [50, 0],
    [100, 5],
  ];

  it("joins the points into a line", () => {
    expect(linePath(points)).toBe("M0 10L50 0L100 5");
  });

  it("closes the line down to the baseline for the area", () => {
    expect(areaPath(points, 40)).toBe("M0 10L50 0L100 5L100 40L0 40Z");
  });
});

describe("ratio", () => {
  it("measures a value against the largest one", () => {
    expect(ratio(25, 100)).toBe(0.25);
  });

  it("is zero against an empty maximum", () => {
    expect(ratio(5, 0)).toBe(0);
  });
});

describe("shares", () => {
  it("turns values into percents of their sum", () => {
    expect(shares([120, 60, 20])).toEqual([60, 30, 10]);
  });

  it("gives nothing to an empty total", () => {
    expect(shares([0, 0])).toEqual([0, 0]);
  });
});
