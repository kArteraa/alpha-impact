import type { ClaimType, SourceRef } from "../types";

export const CLAIM_BADGES: Record<ClaimType, { label: string; icon: string }> = {
  fact: { label: "Факт", icon: "■" },
  bank: { label: "Банк", icon: "◆" },
  ai: { label: "AI", icon: "✦" },
};

export const SOURCE_KINDS: Record<SourceRef["kind"], { label: string; icon: string }> = {
  news: { label: "новость", icon: "≡" },
  house_view: { label: "отчёт банка", icon: "◆" },
  profile: { label: "данные компании", icon: "▣" },
  graph: { label: "данные компании", icon: "▣" },
  calc: { label: "расчёт", icon: "∑" },
};

export const TRAIT_SOURCES: ReadonlySet<SourceRef["kind"]> = new Set(["profile", "graph"]);

export const SIGNIFICANCE_LEVELS = 3;

export function significanceLevel(significance: number): number {
  return Math.min(SIGNIFICANCE_LEVELS, Math.max(1, Math.ceil(significance * SIGNIFICANCE_LEVELS)));
}

export function sourceTitle(source: SourceRef): string {
  return source.title ?? source.id;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { timeZone: "UTC" });
}
