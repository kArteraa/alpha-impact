import { describe, expect, it } from "vitest";
import tokens from "./tokens.css?raw";

const DECLARATION = /(--[\w-]+)\s*:\s*([^;]+);/g;

function declarations(block: string): Map<string, string> {
  return new Map(Array.from(block.matchAll(DECLARATION), ([, name, value]) => [name, value.trim()]));
}

function block(selector: string): string {
  const start = tokens.indexOf(selector);
  expect(start).toBeGreaterThanOrEqual(0);
  const open = tokens.indexOf("{", start);
  return tokens.slice(open + 1, tokens.indexOf("}", open));
}

describe("design tokens", () => {
  const light = declarations(block(":root {"));
  const systemDark = declarations(block(':root:not([data-theme="light"])'));
  const forcedDark = declarations(block(':root[data-theme="dark"]'));

  it("uses the same dark values for the system setting and the forced theme", () => {
    expect(forcedDark).toEqual(systemDark);
  });

  it("redefines in dark only tokens the light theme has", () => {
    expect([...systemDark.keys()].filter((name) => !light.has(name))).toEqual([]);
  });

  it("keeps the font in the font stack without loading files", () => {
    expect(light.get("--font-family")).toMatch(/^Inter,/);
    expect(tokens).not.toMatch(/@font-face|@import|url\(/);
  });
});
