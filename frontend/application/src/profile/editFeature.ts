import type { Feature } from "@alpha-impact/plugin";

const NUMBER = new Intl.NumberFormat("ru-RU");

export function isEditable(feature: Feature): boolean {
  return feature.source !== "bank";
}

export function formatFeatureValue(value: Feature["value"]): string {
  if (value === null) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "да" : "нет";
  }
  if (typeof value === "number") {
    return NUMBER.format(value);
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return value;
}
