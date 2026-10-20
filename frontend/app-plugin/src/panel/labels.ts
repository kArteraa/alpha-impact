import type { ClaimType, SourceRef } from "../types";

export const CLAIM_BADGES: Record<ClaimType, { label: string; icon: string }> = {
  fact: { label: "Факт", icon: "■" },
  bank: { label: "Банк", icon: "◆" },
  ai: { label: "AI", icon: "✦" },
};

export const SOURCE_KINDS: Record<SourceRef["kind"], { label: string; icon: string; trait: boolean }> = {
  news: { label: "новость", icon: "≡", trait: false },
  house_view: { label: "отчёт банка", icon: "◆", trait: false },
  profile: { label: "данные компании", icon: "▣", trait: true },
  graph: { label: "данные компании", icon: "▣", trait: true },
  calc: { label: "расчёт", icon: "∑", trait: false },
};

export const SIGNIFICANCE_LEVELS = 3;

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });

export function significanceLevel(significance: number): number {
  return Math.min(SIGNIFICANCE_LEVELS, Math.max(1, Math.ceil(significance * SIGNIFICANCE_LEVELS)));
}

export function sourceTitle(source: SourceRef): string {
  return source.title ?? source.id;
}

export function formatDate(iso: string): string | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : DATE.format(date);
}
