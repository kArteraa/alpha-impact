import type { ClaimType, InsightCard, SourceRef } from "@alpha-impact/plugin";

const SOURCES: Record<ClaimType, SourceRef> = {
  fact: { kind: "news", id: "news-feed", title: "Лента новостей", url: null, published_at: null },
  bank: { kind: "house_view", id: "hv-feed", title: "Обзор Альфа-Банка", url: null, published_at: null },
  ai: { kind: "calc", id: "calc-feed", title: "Расчёт Alpha Impact", url: null, published_at: null },
};

function event(id: string, headline: string, why: string, significance: number, types: ClaimType[]): InsightCard {
  return {
    id,
    headline,
    significance,
    trace_id: "trace-mock-1",
    why_for_you: types.map((type) => ({ text: why, type, source_ref: SOURCES[type] })),
    what_happened: [],
    consequences: [],
    actions: [],
    bank_view: [],
    basis: types.map((type) => SOURCES[type]),
  };
}

export const EVENTS: Record<string, InsightCard[]> = {
  client_wholesale: [
    event("ev-logistics", "Логистика в убытке", "43% ваших платежей уходит перевозчикам и складам", 0.8, ["fact", "bank", "ai"]),
    event("ev-yuan", "Юань дорожает к рублю", "12% закупок оплачиваются в юанях", 0.6, ["fact", "ai"]),
    event("ev-rate", "Банк ждёт снижения ключевой ставки", "Кредитная линия с плавающей ставкой", 0.7, ["bank", "ai"]),
    event("ev-retail", "Розничный спрос в регионах замедлился", "Половина выручки — сети в Поволжье", 0.4, ["fact"]),
  ],
  client_construction: [
    event("ev-cement", "Цемент подорожал на 9%", "Цемент — крупнейшая статья закупок", 0.9, ["fact", "ai"]),
    event("ev-leasing", "Лизинговые ставки растут", "Техника в лизинге с плавающей ставкой", 0.7, ["bank", "ai"]),
    event("ev-mortgage", "Льготная ипотека сокращается", "Застройщики — основные заказчики", 0.6, ["fact", "bank"]),
  ],
};
