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

export const PAGE_DOMAINS: Record<PageType, readonly string[]> = {
  article: [
    "kommersant.ru",
    "vedomosti.ru",
    "interfax.ru",
    "rbc.ru",
    "tass.ru",
    "forbes.ru",
    "frankmedia.ru",
    "expert.ru",
  ],
  counterparty: ["rusprofile.ru", "checko.ru", "list-org.com", "focus.kontur.ru", "zachestnyibiznes.ru", "sbis.ru"],
  tender: [
    "zakupki.gov.ru",
    "rts-tender.ru",
    "223.rts-tender.ru",
    "sberbank-ast.ru",
    "roseltorg.ru",
    "b2b-center.ru",
    "fabrikant.ru",
  ],
  fx_rate: ["cbr.ru", "moex.com", "investing.com", "ru.investing.com", "profinance.ru"],
};

export const PAGE_TEXT_MAX_CHARS = 2000;

export const TRACKING_PARAMS = ["from", "yclid", "gclid", "fbclid", "_openstat"];

export const TRACKING_PREFIX = "utm_";

export const ARTICLE_MIN_CHARS = 300;

export const FX_CURRENCY_CODES = ["USD", "EUR", "CNY"];

export const TENDER_SUBJECT_LABELS = [
  "Объект закупки",
  "Наименование объекта закупки",
  "Предмет закупки",
  "Предмет договора",
  "Наименование закупки",
];
