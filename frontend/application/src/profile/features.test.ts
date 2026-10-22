import type { Feature } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { featureText, formatFeatureValue, groupFeatures, isEditable } from "./features";

const bankFact: Feature = { value: "Оптовая торговля", source: "bank", confidence: 1, updated_at: "2026-10-01T00:00:00Z" };
const derived: Feature = { value: true, source: "inferred", confidence: 0.7, updated_at: "2026-10-01T00:00:00Z" };

describe("profile features", () => {
  it("lets the client edit derived traits but not bank facts", () => {
    expect(isEditable(bankFact)).toBe(false);
    expect(isEditable(derived)).toBe(true);
    expect(isEditable({ ...derived, source: "graph" })).toBe(true);
    expect(isEditable({ ...derived, source: "user" })).toBe(true);
  });

  it.each([
    [true, "да"],
    [false, "нет"],
    [["юани", "дирхамы"], "юани, дирхамы"],
    [43, "43"],
    [18_500_000_000, "18 500 000 000"],
    [null, "—"],
    ["крупный", "крупный"],
  ] as const)("shows %j as %s", (value, text) => {
    expect(formatFeatureValue(value as Feature["value"]).replace(/\s/g, " ")).toBe(text);
  });
});

describe("featureText", () => {
  it.each([
    ["industry_class", "wholesale", "Оптовая торговля"],
    ["industry_class", "Строительство", "Строительство"],
    ["products", ["settlement", "loan", "payroll"], "Расчётный счёт, Кредит, Зарплатный проект"],
    ["cl_type", "CLIENT", "Действующий клиент"],
    ["ownership", "ЧАСТНАЯ СОБСТВЕННОСТЬ", "Частная собственность"],
    ["import_countries", ["КИТАЙ", "ТУРЦИЯ"], "Китай, Турция"],
    ["okved_code", "46.49", "46.49"],
    ["region", "Москва", "Москва"],
    ["revenue_rub", 24_107_304_489, "24 107 304 489 ₽"],
    ["workers", "Более 251", "Более 251"],
  ] as const)("shows %s %j as %s", (name, value, text) => {
    expect(featureText(name, value as Feature["value"]).replace(/\s/g, " ")).toBe(text);
  });
});

describe("groupFeatures", () => {
  it("splits the known features into titled groups in a fixed order", () => {
    expect(groupFeatures(["products", "region", "industry_class", "workers", "okved_code"])).toEqual([
      { title: "Компания", names: ["industry_class", "okved_code"] },
      { title: "География", names: ["region"] },
      { title: "Масштаб", names: ["workers"] },
      { title: "Отношения с банком", names: ["products"] },
    ]);
  });

  it("skips groups the profile has nothing for", () => {
    expect(groupFeatures(["region"])).toEqual([{ title: "География", names: ["region"] }]);
  });

  it("leaves out features it does not know", () => {
    expect(groupFeatures(["mystery"])).toEqual([]);
  });
});
