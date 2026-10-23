import { type ActionContext, type InterpretRequest, type LoanContext, ROLE_LABELS, type TraceStep } from "@alpha-impact/plugin";
import { NUMBER, RUB_WHOLE } from "../money";
import { DAYS, plural } from "../ui/plural";

const STEP_NAMES: Record<string, string> = {
  "profile.get_profile": "Профиль компании",
  "counterparty.context": "Агрегаты получателя",
  "news.annotate": "Разметка вставленной новости",
  "house_view.claims": "Позиция банка по теме",
  "house_view.chain": "Версии утверждения банка",
  "trace.find_by_card": "Трасса исходной карточки",
  "whatif.deposit_terms": "Расчёт депозита",
  "whatif.rate_burden": "Расчёт плавающей ставки",
  relevance: "Отбор новостей",
  plan: "План агента",
  draft: "Черновик карточки",
  redraft: "Переписанный черновик",
  card: "Итог: карточка",
  silent: "Итог: молчание",
  failed: "Итог: ошибка",
};

const CRITIC_ROUND = /^round (\d+)$/;

export function stepLabel(step: TraceStep): string {
  const round = step.step === "critic" ? CRITIC_ROUND.exec(step.name) : null;
  if (round) {
    return `Критик, круг ${round[1]}`;
  }
  return Object.hasOwn(STEP_NAMES, step.name) ? STEP_NAMES[step.name] : step.name;
}

const VERDICT = /^(\d+): (.*)$/s;
const CODED = /^(\w+): (.*)$/s;
const VERDICT_PASSED = "ok";
const VERDICT_CODES: Record<string, string> = {
  source: "Источник",
  bank: "Позиция банка",
  contradiction: "Противоречие",
  retelling: "Пересказ",
  error: "Сбой",
};

export function verdictLabel(verdict: string): { text: string; ok: boolean } {
  const match = VERDICT.exec(verdict);
  if (!match) {
    return { text: verdict, ok: false };
  }
  const [, round, body] = match;
  if (body === VERDICT_PASSED) {
    return { text: `Круг ${round}: замечаний нет`, ok: true };
  }
  const coded = CODED.exec(body);
  if (!coded || !Object.hasOwn(VERDICT_CODES, coded[1])) {
    return { text: `Круг ${round}: ${body}`, ok: false };
  }
  return { text: `Круг ${round}: ${VERDICT_CODES[coded[1]]} — ${coded[2]}`, ok: false };
}

const LOAN_PRODUCTS: Record<LoanContext["product"], string> = {
  loan: "Кредит",
  leasing: "Лизинг",
  guarantee: "Гарантия",
};

const RATE_TYPES: Record<NonNullable<LoanContext["rate_type"]>, string> = {
  floating: "плавающая ставка",
  fixed: "фиксированная ставка",
};

function actionLabel(action: ActionContext): string {
  switch (action.type) {
    case "payment":
      return `Платёж ${RUB_WHOLE.format(action.amount)}`;
    case "deposit":
      return `Депозит ${RUB_WHOLE.format(action.amount)} на ${plural(action.term_days, DAYS)}`;
    case "loan": {
      const loan = `${LOAN_PRODUCTS[action.product]} ${RUB_WHOLE.format(action.amount)}`;
      return action.rate_type ? `${loan}, ${RATE_TYPES[action.rate_type]}` : loan;
    }
    case "fx":
      return `Валютная операция ${NUMBER.format(action.amount)} ${action.currency}`;
    case "payroll":
      return `Зарплата ${RUB_WHOLE.format(action.amount)}`;
    case "dashboard":
      return "Лента главного экрана";
    case "page":
      return "Вставленная новость";
    case "followup":
      return `Вопрос к карточке: «${action.question}»`;
    default:
      return "";
  }
}

export function requestLabel(request: InterpretRequest): string {
  return [actionLabel(request.action_context), ROLE_LABELS[request.role]].filter(Boolean).join(" · ");
}
