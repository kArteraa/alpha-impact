import type { Feature } from "@alpha-impact/plugin";
import { FEATURE_GROUPS, FEATURES } from "../data/profile";
import { NUMBER, RUB_WHOLE } from "../money";

export interface FeatureSection {
  title: string;
  names: string[];
}

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

export function featureText(name: string, value: Feature["value"]): string {
  const spec = FEATURES[name];
  const labels = spec?.labels ?? {};
  const word = (item: string) => labels[item] ?? item;
  if (typeof value === "string") {
    return word(value);
  }
  if (Array.isArray(value)) {
    return value.map(word).join(", ");
  }
  if (typeof value === "number" && spec?.money) {
    return RUB_WHOLE.format(value);
  }
  return formatFeatureValue(value);
}

export function groupFeatures(names: readonly string[]): FeatureSection[] {
  return FEATURE_GROUPS.map(([group, title]) => ({
    title,
    names: Object.keys(FEATURES).filter((name) => FEATURES[name].group === group && names.includes(name)),
  })).filter((section) => section.names.length > 0);
}
