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

export const FEATURE_LABELS: Record<string, string> = {
  industry_class: "Отрасль",
  okved_name: "Основной вид деятельности",
  okved_code: "Код ОКВЭД",
  company_age: "Возраст компании, лет",
  eco_stage: "Стадия развития",
  ownership: "Форма собственности",
  region: "Регион",
  city: "Город",
  import_countries: "Страны импорта",
  revenue_rub: "Выручка",
  workers: "Сотрудников",
  cl_type: "Статус клиента",
  products: "Продукты банка",
};

export const COUNTERPARTY_LABELS: Record<string, string> = {
  industry_class: "Отрасль получателя",
  region: "Регион получателя",
  size_bucket: "Размер получателя",
  share_of_client_outflow: "Доля сегмента получателя в оттоке компании",
  share_of_counterparty_inflow: "Доля компании в поступлениях сегмента получателя",
  confidence: "Надёжность оценки получателя",
};

const NAMED_SOURCES: Partial<Record<SourceRef["kind"], Record<string, string>>> = {
  profile: FEATURE_LABELS,
  graph: COUNTERPARTY_LABELS,
};

export const CALCULATION_TITLES = new Map([
  ["deposit_terms", "Выгода фиксации ставки против помесячного переразмещения"],
  ["rate_burden", "Изменение процентных расходов при плавающей ставке"],
]);

export const SIGNIFICANCE_LEVELS = 3;

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });
const KOPECK_DIGITS = 2;
const CURRENCY_CODE = /^[A-Z]{3}$/;
const HYPHEN_MINUS = "-";
const MINUS_SIGN = "−";

export function significanceLevel(significance: number): number {
  return Math.min(SIGNIFICANCE_LEVELS, Math.max(1, Math.ceil(significance * SIGNIFICANCE_LEVELS)));
}

export function knownTitle(source: SourceRef): string | null {
  const names = NAMED_SOURCES[source.kind];
  return names && Object.hasOwn(names, source.id) ? names[source.id] : (source.title ?? null);
}

export function sourceTitle(source: SourceRef): string {
  return knownTitle(source) ?? source.id;
}

export function formatValue(value: number, unit: string): string {
  const digits = Number.isInteger(value) ? 0 : KOPECK_DIGITS;
  const number: Intl.NumberFormatOptions = {
    signDisplay: "exceptZero",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  };
  const text = CURRENCY_CODE.test(unit)
    ? new Intl.NumberFormat("ru-RU", { ...number, style: "currency", currency: unit }).format(value)
    : `${new Intl.NumberFormat("ru-RU", number).format(value)} ${unit}`;
  return text.replace(HYPHEN_MINUS, MINUS_SIGN);
}

export function formatDate(iso: string): string | null {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : DATE.format(date);
}
