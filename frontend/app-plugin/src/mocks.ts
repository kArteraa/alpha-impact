import type { InsightCard, InterpretResponse, SourceRef } from "./types";

const report: SourceRef = {
  kind: "house_view",
  id: "hv-logistics-2026-09-07",
  title: "Обзор отраслей Альфа-Банка, 07.09.2026, стр. 4",
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
  title: "Доля логистики в оттоке компании",
  url: null,
  published_at: null,
};

const card: InsightCard = {
  id: "card-mock-1",
  headline: "Логистика и склады в убытке: платёж перевозчику",
  what_happened: [
    {
      text: "Логистика и складской бизнес показали убыток по итогам квартала",
      type: "fact",
      source_ref: news,
    },
  ],
  why_for_you: [
    { text: "43% оттока компании уходит перевозчикам и складам", type: "fact", source_ref: graph },
  ],
  consequences: [
    {
      text: "Вероятен рост тарифов и срыв сроков у перевозчиков в ближайший квартал",
      type: "ai",
      source_ref: news,
    },
  ],
  actions: [
    {
      text: "Закрепить тарифы и сроки в договоре до конца года",
      type: "ai",
      source_ref: report,
    },
  ],
  bank_view: [
    {
      text: "Банк ждёт давления на маржу логистики до конца 2026 года",
      type: "bank",
      source_ref: report,
    },
  ],
  basis: [news, report, graph],
  product_offer: {
    product: "Аккредитив",
    reason: "Платёж контрагенту из отрасли под давлением",
    rule_id: "stress-industry-payment",
  },
  significance: 0.8,
  needs_review: false,
  trace_id: "trace-mock-1",
};

export const mockResponses = {
  checking: undefined,
  silent: {
    silent: true,
    silent_reason: "Нет релевантных событий по этому действию",
    cards: [],
    cached: false,
  } satisfies InterpretResponse,
  cards: { silent: false, silent_reason: null, cards: [card], cached: false } satisfies InterpretResponse,
};
