import type { Feature } from "@alpha-impact/plugin";
import { FEATURE_GROUPS, FEATURES } from "../data/profile";
import { NUMBER, RUB_WHOLE } from "../money";

export interface FeatureSection {
  title: string;
  names: string[];
}

const SHOUTING = /\p{Lu}/u;

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

function calm(text: string): string {
  if (!SHOUTING.test(text) || text !== text.toUpperCase()) {
    return text;
  }
  const lower = text.toLowerCase();
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

export function featureText(name: string, value: Feature["value"]): string {
  const spec = FEATURES[name];
  const labels = spec?.options ?? spec?.labels ?? {};
  const word = (item: string) => labels[item] ?? calm(item);
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
