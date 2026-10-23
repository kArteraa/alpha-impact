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

export const CALCULATION_TITLES = new Map([
  ["deposit_terms", "Выгода фиксации ставки против помесячного переразмещения"],
  ["rate_burden", "Изменение процентных расходов при плавающей ставке"],
]);

export const SIGNIFICANCE_LEVELS = 3;

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });
const KOPECK_DIGITS = 2;
const CURRENCY_CODE = /^[A-Z]{3}$/;

export function significanceLevel(significance: number): number {
  return Math.min(SIGNIFICANCE_LEVELS, Math.max(1, Math.ceil(significance * SIGNIFICANCE_LEVELS)));
}

export function sourceTitle(source: SourceRef): string {
  return source.title ?? source.id;
}

export function formatValue(value: number, unit: string): string {
  const digits = Number.isInteger(value) ? 0 : KOPECK_DIGITS;
  const number: Intl.NumberFormatOptions = {
    signDisplay: "exceptZero",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  };
  if (CURRENCY_CODE.test(unit)) {
    return new Intl.NumberFormat("ru-RU", { ...number, style: "currency", currency: unit }).format(value);
  }
  return `${new Intl.NumberFormat("ru-RU", number).format(value)} ${unit}`;
}

export function formatDate(iso: string): string | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : DATE.format(date);
}
