import type { InsightCard, InterpretResponse, SourceRef } from "./types";

const report: SourceRef = {
  kind: "house_view",
  id: "hv-logistics-2026-09-07",
  title: "Обзор отраслей Альфа-Банка, стр. 4",
  url: null,
  published_at: "2026-09-07T00:00:00Z",
};

const news: SourceRef = {
  kind: "news",
  id: "news-mock-1",
  title: "Склады маркетплейсов и перевозчики ушли в убыток",
  url: "https://example.com/news/logistics",
  published_at: "2026-10-18T09:00:00Z",
};

const graph: SourceRef = {
  kind: "graph",
  id: "client-outflow-logistics",
  title: "43% платежей — логистика",
  url: null,
  published_at: null,
};

const profile: SourceRef = {
  kind: "profile",
  id: "profile-leasing",
  title: "лизинг",
  url: null,
  published_at: null,
};

const calc: SourceRef = {
  kind: "calc",
  id: "whatif-rate-burden",
  title: "Расчёт нагрузки по ставке",
  url: null,
  published_at: null,
};

const card: InsightCard = {
  id: "card-mock-1",
  headline: "Логистика в убытке: платёж перевозчику",
  why_for_you: [
    { text: "Почти половина ваших платежей уходит перевозчикам и складам", type: "fact", source_ref: graph },
    { text: "Парк в лизинге: рост тарифов ляжет на себестоимость доставки", type: "ai", source_ref: profile },
  ],
  what_happened: [
    {
      text: "Логистика и складской бизнес показали убыток по итогам квартала",
      type: "fact",
      source_ref: news,
    },
  ],
  consequences: [
    {
      text: "Вероятен рост тарифов и срыв сроков у перевозчиков в ближайший квартал",
      type: "ai",
      source_ref: news,
    },
    { text: "Нагрузка на бюджет доставки вырастет примерно на 6%", type: "ai", source_ref: calc },
  ],
  actions: [
    { text: "Закрепить тарифы и сроки в договоре до конца года", type: "ai", source_ref: report },
    { text: "Проверить запасной перевозчик на ключевых маршрутах", type: "ai", source_ref: graph },
  ],
  bank_view: [
    {
      text: "Банк ждёт давления на маржу логистики до конца 2026 года",
      type: "bank",
      source_ref: report,
    },
  ],
  basis: [news, report, graph, profile, calc],
  product_offer: {
    product: "Аккредитив",
    reason: "Платёж контрагенту из отрасли под давлением",
    rule_id: "stress-industry-payment",
  },
  significance: 0.8,
  needs_review: false,
  trace_id: "trace-mock-1",
};

const updatedCard: InsightCard = {
  ...card,
  id: "card-mock-2",
  headline: "Логистика в убытке: крупный платёж перевозчику",
  significance: 0.95,
};

export const mockResponses = {
  checking: undefined,
  silent: {
    silent: true,
    silent_reason: "По этому контрагенту нет новостей и позиций банка за последний месяц",
    cards: [],
    cached: false,
  } satisfies InterpretResponse,
  cards: { silent: false, silent_reason: null, cards: [card], cached: false } satisfies InterpretResponse,
  updated: { silent: false, silent_reason: null, cards: [updatedCard], cached: false } satisfies InterpretResponse,
};
