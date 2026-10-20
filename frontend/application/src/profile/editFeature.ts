import type { Feature } from "@alpha-impact/plugin";

export type Features = Record<string, Feature>;

export function isEditable(feature: Feature): boolean {
  return feature.source !== "bank";
}

export function editFeature(features: Features, key: string, value: string): Features {
  const feature = features[key];
  if (!isEditable(feature)) {
    throw new Error(`Bank fact ${key} is read-only`);
  }
  return { ...features, [key]: { ...feature, value, source: "user" } };
}

export function formatFeatureValue(value: Feature["value"]): string {
  if (value === null) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "да" : "нет";
  }
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  return String(value);
}
