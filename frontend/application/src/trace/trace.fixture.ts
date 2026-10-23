import type { InsightCard, SourceRef, Trace, TraceStep } from "@alpha-impact/plugin";

const MODEL = "z-ai/glm-5.3-flash";
const START = Date.parse("2026-10-23T08:15:00.000Z");

export const NEWS_SOURCE: SourceRef = {
  kind: "news",
  id: "4befb3e28f2e79ee3ffbf3c808413e4b",
  title: "Перевозчики подняли тарифы на междугородние рейсы",
  url: "https://www.kommersant.ru/doc/7000001",
  published_at: "2026-10-21T07:30:00Z",
};

export const REPORT_SOURCE: SourceRef = {
  kind: "house_view",
  id: "8ad8e275a1bc5a6285575776eb6af55d",
  title: "ALFA-7M26.pdf, стр. 1",
  url: "/reports/ALFA-7M26.pdf#page=1",
  published_at: null,
};

const GRAPH_SOURCE: SourceRef = {
  kind: "graph",
  id: "share_of_client_outflow",
  title: "Контекст контрагента: share_of_client_outflow",
  url: null,
  published_at: null,
};

const CARD: InsightCard = {
  id: "0f9d1c52-6a43-4b8e-9d0c-1e2f3a4b5c6d",
  trace_id: "5e60de14-6b46-407c-8f00-33a5bcf44446",
  headline: "Перевозчики дорожают: платёж логистической компании",
  significance: 0.8,
  needs_review: false,
  what_happened: [{ text: "Перевозчики подняли тарифы на 7%", type: "fact", source_ref: NEWS_SOURCE }],
  why_for_you: [{ text: "На логистику уходит 43% ваших платежей", type: "fact", source_ref: GRAPH_SOURCE }],
  consequences: [{ text: "Стоимость доставки вырастет в ближайший месяц", type: "ai", source_ref: NEWS_SOURCE }],
  actions: [{ text: "Зафиксировать тариф в договоре до конца квартала", type: "ai", source_ref: NEWS_SOURCE }],
  bank_view: [
    { text: "Банк ждёт роста издержек в логистике и складах", type: "bank", source_ref: REPORT_SOURCE },
  ],
  basis: [NEWS_SOURCE, GRAPH_SOURCE, REPORT_SOURCE],
};

function step(offsetMs: number, fields: Omit<TraceStep, "started_at">): TraceStep {
  return { ...fields, started_at: new Date(START + offsetMs).toISOString() };
}

export const TRACE: Trace = {
  id: "5e60de14-6b46-407c-8f00-33a5bcf44446",
  created_at: "2026-10-23T08:15:00Z",
  request: {
    action_context: { type: "payment", amount: 1_500_000, beneficiary_id: "U_96105" },
    client_id: "U_1941",
    role: "cfo",
    user_id: "user_cfo_wholesale",
  },
  result: { silent: false, cards: [CARD] },
  critic_verdicts: ["1: retelling: карточка опирается меньше чем на два источника", "2: ok"],
  steps: [
    step(0, {
      step: "tool",
      name: "profile.get_profile",
      duration_ms: 3,
      input_summary: "authorized client features",
      output_summary: '{"client_id": "U_1941", "features": {"industry_class": {"value": "wholesale"}}}',
    }),
    step(3, {
      step: "tool",
      name: "counterparty.context",
      duration_ms: 12,
      input_summary: "recipient aggregates",
      output_summary: '{"industry_class": "logistics", "share_of_client_outflow": 0.43}',
    }),
    step(15, {
      step: "prefilter",
      name: "relevance",
      duration_ms: 45,
      input_summary: "limit=200",
      output_summary: '{"candidates": ["4befb3e28f2e79ee3ffbf3c808413e4b"], "house_view": ["8ad8e275a1bc5a6285575776eb6af55d"]}',
    }),
    step(60, {
      step: "plan",
      name: "plan",
      model: MODEL,
      duration_ms: 4_700,
      tokens_in: 4_812,
      tokens_out: 236,
      cost_rub: 0.06,
      input_summary: "11639 characters of structured context",
      output_summary: '{"focus": "Рост тарифов перевозчиков", "tools": [{"tool": "house_view.claims", "argument": "trade_logistics"}]}',
    }),
    step(4_760, {
      step: "tool",
      name: "house_view.claims",
      duration_ms: 20,
      input_summary: "trade_logistics",
      output_summary: '[{"id": "8ad8e275a1bc5a6285575776eb6af55d", "claim": "Банк ждёт роста издержек в логистике и складах"}]',
    }),
    step(4_780, {
      step: "draft",
      name: "draft",
      model: MODEL,
      duration_ms: 7_200,
      tokens_in: 9_870,
      tokens_out: 1_140,
      cost_rub: 0.21,
      input_summary: "15204 characters of structured context",
      output_summary: '{"headline": "Перевозчики дорожают", "what_happened": [{"text": "Перевозчики подняли тарифы на 7%"',
    }),
    step(11_980, {
      step: "critic",
      name: "round 1",
      duration_ms: 1_900,
      tokens_in: 1_610,
      tokens_out: 40,
      cost_rub: 0.02,
      input_summary: "card 0f9d1c52-6a43-4b8e-9d0c-1e2f3a4b5c6d, 2 sources",
      output_summary: '["retelling: карточка опирается меньше чем на два источника"]',
    }),
    step(13_880, {
      step: "draft",
      name: "redraft",
      model: MODEL,
      duration_ms: 6_400,
      tokens_in: 10_950,
      tokens_out: 1_090,
      cost_rub: 0.22,
      input_summary: "17120 characters of structured context",
      output_summary: '{"headline": "Перевозчики дорожают: платёж логистической компании"',
    }),
    step(20_280, {
      step: "critic",
      name: "round 2",
      duration_ms: 1_700,
      tokens_in: 1_590,
      tokens_out: 30,
      cost_rub: 0.02,
      input_summary: "card 0f9d1c52-6a43-4b8e-9d0c-1e2f3a4b5c6d, 3 sources",
      output_summary: "[]",
    }),
    step(21_980, {
      step: "final",
      name: "card",
      duration_ms: 0,
      input_summary: "",
      output_summary: "1 cards",
    }),
  ],
};
