import type { Feature } from "@alpha-impact/plugin";

const UPDATED = "2026-10-01T00:00:00Z";

export const FEATURE_LABELS: Record<string, string> = {
  industry: "Отрасль",
  region: "Регион",
  size: "Размер компании",
  logistics_share: "Доля логистики в платежах",
  leasing: "Лизинг",
  fx_purchases: "Закупки в валюте",
};

export const PROFILE_FEATURES: Record<string, Feature> = {
  industry: { value: "Оптовая торговля", source: "bank", confidence: 1, updated_at: UPDATED },
  region: { value: "Самарская область", source: "bank", confidence: 1, updated_at: UPDATED },
  size: { value: "крупный", source: "bank", confidence: 1, updated_at: UPDATED },
  logistics_share: { value: "43%", source: "graph", confidence: 0.9, updated_at: UPDATED },
  leasing: { value: true, source: "inferred", confidence: 0.7, updated_at: UPDATED },
  fx_purchases: { value: ["юани"], source: "inferred", confidence: 0.6, updated_at: UPDATED },
};
