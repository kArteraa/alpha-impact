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

export function featureText(name: string, value: Feature["value"]): string {
  const spec = FEATURES[name];
  const labels = spec?.labels ?? {};
  const word = (item: string) => (Object.hasOwn(labels, item) ? labels[item] : item);
  if (typeof value === "string") {
    return word(value);
  }
  if (Array.isArray(value)) {
    return value.map(word).join(", ");
  }
  if (typeof value === "number") {
    return spec?.money ? RUB_WHOLE.format(value) : NUMBER.format(value);
  }
  if (value === null) {
    return "—";
  }
  return value ? "да" : "нет";
}

export function groupFeatures(names: readonly string[]): FeatureSection[] {
  return FEATURE_GROUPS.map(([group, title]) => ({
    title,
    names: Object.keys(FEATURES).filter((name) => FEATURES[name].group === group && names.includes(name)),
  })).filter((section) => section.names.length > 0);
}
