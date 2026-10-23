import type { ClaimType, InsightCard, InterpretResponse, SourceRef } from "@alpha-impact/plugin";

const SOURCES: Record<ClaimType, SourceRef> = {
  fact: { kind: "news", id: "news-feed", title: "Лента новостей", url: null, published_at: null },
  bank: { kind: "house_view", id: "hv-feed", title: "Обзор Альфа-Банка", url: null, published_at: null },
  ai: { kind: "calc", id: "calc-feed", title: "Расчёт Alpha Impact", url: null, published_at: null },
};

function event(id: string, headline: string, consequence: string, significance: number, types: ClaimType[]): InsightCard {
  const claims = types.map((type) => ({ text: consequence, type, source_ref: SOURCES[type] }));
  return {
    id,
    headline,
    significance,
    trace_id: "trace-mock-1",
    what_happened: [],
    why_for_you: [],
    consequences: claims,
    actions: [],
    bank_view: [],
    basis: types.map((type) => SOURCES[type]),
  };
}

const FEEDS: Record<string, InsightCard[]> = {
  U_1941: [
    event("ev-logistics", "Логистика в убытке", "Перевозчики могут поднять тарифы: им уходит 43% платежей", 0.8, ["fact", "bank", "ai"]),
    event("ev-rate", "Банк ждёт снижения ключевой ставки", "Платёж по кредитной линии с плавающей ставкой снизится", 0.7, ["bank", "ai"]),
    event("ev-yuan", "Юань дорожает к рублю", "Закупки в юанях подорожают: это 12% оплат", 0.6, ["fact", "ai"]),
    event("ev-retail", "Розничный спрос в регионах замедлился", "Выручка от сетей в Поволжье может просесть", 0.4, ["fact"]),
  ],
  U_9250: [
    event("ev-cement", "Цемент подорожал на 9%", "Себестоимость объектов вырастет: цемент — крупнейшая статья закупок", 0.9, ["fact", "ai"]),
    event("ev-leasing", "Лизинговые ставки растут", "Платежи за технику в лизинге вырастут", 0.7, ["bank", "ai"]),
    event("ev-mortgage", "Льготная ипотека сокращается", "Заказов от застройщиков может стать меньше", 0.6, ["fact", "bank"]),
  ],
};

export function feedOf(clientId: string): InterpretResponse {
  return { silent: false, cards: FEEDS[clientId] ?? [] };
}

export const SILENT_FEED: InterpretResponse = {
  silent: true,
  silent_reason: "Нет значимых событий для этого действия",
  cards: [],
};
