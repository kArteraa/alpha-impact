import type { InterpretRequest, TraceStep } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { requestLabel, stepLabel, verdictLabel } from "./labels";

function named(step: TraceStep["step"], name: string): TraceStep {
  return { step, name, input_summary: "", output_summary: "", started_at: "2026-10-23T08:15:00Z" };
}

function asked(action_context: InterpretRequest["action_context"]): InterpretRequest {
  return { action_context, client_id: "U_1941", role: "treasurer", user_id: "user_cfo_wholesale" };
}

describe("stepLabel", () => {
  it.each([
    ["tool", "profile.get_profile", "Профиль компании"],
    ["tool", "counterparty.context", "Агрегаты получателя"],
    ["tool", "news.annotate", "Разметка вставленной новости"],
    ["tool", "house_view.claims", "Позиция банка по теме"],
    ["tool", "house_view.chain", "Версии утверждения банка"],
    ["tool", "trace.find_by_card", "Трасса исходной карточки"],
    ["tool", "whatif.deposit_terms", "Расчёт депозита"],
    ["tool", "whatif.rate_burden", "Расчёт плавающей ставки"],
    ["prefilter", "relevance", "Отбор новостей"],
    ["plan", "plan", "План агента"],
    ["draft", "draft", "Черновик карточки"],
    ["draft", "redraft", "Переписанный черновик"],
    ["critic", "round 1", "Критик, круг 1"],
    ["critic", "round 2", "Критик, круг 2"],
    ["critic", "round 1 build", "Сборка карточки, круг 1"],
    ["final", "card", "Итог: карточка"],
    ["final", "silent", "Итог: молчание"],
    ["final", "failed", "Итог: ошибка"],
  ] as const)("names the %s step %s in Russian", (kind, name, label) => {
    expect(stepLabel(named(kind, name))).toBe(label);
  });

  it("shows an unknown step as it is", () => {
    expect(stepLabel(named("tool", "news.search"))).toBe("news.search");
  });
});

describe("verdictLabel", () => {
  it("says the round passed", () => {
    expect(verdictLabel("2: ok")).toEqual({ text: "Круг 2: замечаний нет", ok: true });
  });

  it.each([
    ["1: source: источник «X» не указан в basis", "Круг 1: Источник — источник «X» не указан в basis"],
    ["1: bank: «X» не цитирует утверждение hv-1 дословно", "Круг 1: Позиция банка — «X» не цитирует утверждение hv-1 дословно"],
    ["2: contradiction: «X» противоречит hv-1: ставка ниже", "Круг 2: Противоречие — «X» противоречит hv-1: ставка ниже"],
    ["1: retelling: карточка опирается меньше чем на два источника", "Круг 1: Пересказ — карточка опирается меньше чем на два источника"],
    ["2: error: BudgetExceeded", "Круг 2: Сбой — BudgetExceeded"],
  ])("names the problem of %s", (verdict, text) => {
    expect(verdictLabel(verdict)).toEqual({ text, ok: false });
  });

  it("shows an unknown verdict as it is", () => {
    expect(verdictLabel("без круга")).toEqual({ text: "без круга", ok: false });
  });
});

describe("requestLabel", () => {
  it.each([
    [{ type: "payment", amount: 1_500_000, beneficiary_id: "U_96105" }, "Платёж 1 500 000 ₽"],
    [{ type: "deposit", amount: 10_000_000, term_days: 90 }, "Депозит 10 000 000 ₽ на 90 дней"],
    [{ type: "deposit", amount: 5_000_000, term_days: 1 }, "Депозит 5 000 000 ₽ на 1 день"],
    [{ type: "loan", amount: 50_000_000, product: "loan", rate_type: "floating" }, "Кредит 50 000 000 ₽, плавающая ставка"],
    [{ type: "loan", amount: 20_000_000, product: "leasing", rate_type: null }, "Лизинг 20 000 000 ₽"],
    [{ type: "loan", amount: 3_000_000, product: "guarantee", rate_type: "fixed" }, "Гарантия 3 000 000 ₽, фиксированная ставка"],
    [{ type: "fx", amount: 100_000, currency: "CNY" }, "Валютная операция 100 000 CNY"],
    [{ type: "payroll", amount: 2_000_000 }, "Зарплата 2 000 000 ₽"],
    [{ type: "dashboard" }, "Лента главного экрана"],
    [{ type: "page", url: "", text: "Текст новости" }, "Вставленная новость"],
    [{ type: "followup", card_id: "card-1", question: "Что с тарифами?" }, "Вопрос к карточке: «Что с тарифами?»"],
  ] as const)("describes %o", (action, label) => {
    expect(requestLabel(asked(action)).replace(/\s/g, " ")).toBe(`${label} · Казначей`);
  });
});
