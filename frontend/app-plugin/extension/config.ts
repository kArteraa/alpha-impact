export const API_BASE = "http://127.0.0.1:8000";

export const CACHE_TTL_MS = 60 * 60 * 1000;

export const PAGE_TYPE_LABELS = {
  article: "Статьи и новости",
  counterparty: "Карточки контрагентов",
  tender: "Тендеры и закупки",
  fx_rate: "Курсы валют",
} as const;

export type PageType = keyof typeof PAGE_TYPE_LABELS;

export const AUTOSHOW_DEFAULT: Record<PageType, boolean> = {
  article: true,
  counterparty: true,
  tender: true,
  fx_rate: true,
};
