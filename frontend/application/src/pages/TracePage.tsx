import type { InterpretRequest, InterpretResponse, Trace, TraceStep } from "@alpha-impact/plugin";
import { useCallback, useId } from "react";
import { Link, useParams } from "react-router";
import { ApiError, api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { Panel } from "../insight/Panel";
import { NUMBER, RUB_FINE, SECONDS } from "../money";
import { requestLabel, stepLabel, verdictLabel } from "../trace/labels";
import { type StepKind, traceSummary } from "../trace/summary";
import { Alert } from "../ui/Alert";
import { ShareBar } from "../ui/charts/ShareBar";
import type { Tone } from "../ui/charts/tone";
import { Icon } from "../ui/Icon";
import { Skeleton } from "../ui/Skeleton";

const WHEN = new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short", timeZone: "Europe/Moscow" });
const MS_IN_SECOND = 1000;
const MISSING = new Set([403, 404]);
const FAILED = "failed";

const PARTS: Record<StepKind, readonly [string, Tone]> = {
  model: ["Модели", "ai"],
  tool: ["Поиск новостей и позиции банка", "bank"],
  service: ["Служебные шаги", "soft"],
};

function stepMeta(step: TraceStep): string {
  const parts: string[] = [];
  if (step.duration_ms) {
    parts.push(`${NUMBER.format(step.duration_ms)} мс`);
  }
  if (step.tokens_in || step.tokens_out) {
    parts.push(`${NUMBER.format(step.tokens_in ?? 0)} → ${NUMBER.format(step.tokens_out ?? 0)} токенов`);
  }
  if (step.model) {
    parts.push(step.model);
  }
  if (step.cost_rub) {
    parts.push(RUB_FINE.format(step.cost_rub));
  }
  return parts.join(" · ");
}

function Summary({ trace }: { trace: Trace }) {
  const summary = traceSummary(trace.steps);
  return (
    <div className="trace-summary">
      <div className="card stat stat-main">
        <span className="muted">Время ответа</span>
        <strong>{SECONDS.format(summary.durationMs / MS_IN_SECOND)} с</strong>
        <ShareBar
          label="На что ушло время"
          items={summary.parts.map((part) => ({
            label: PARTS[part.kind][0],
            value: part.durationMs,
            tone: PARTS[part.kind][1],
            caption: `${NUMBER.format(part.durationMs)} мс`,
          }))}
        />
      </div>
      <dl className="card trace-facts">
        <div>
          <dt>Токены</dt>
          <dd>
            {NUMBER.format(summary.tokensIn)} → {NUMBER.format(summary.tokensOut)}
          </dd>
        </div>
        <div>
          <dt>Модели</dt>
          <dd>{summary.models.join(", ") || "—"}</dd>
        </div>
        <div>
          <dt>Шагов</dt>
          <dd>{trace.steps.length}</dd>
        </div>
        <div>
          <dt>Стоимость</dt>
          <dd>{RUB_FINE.format(summary.costRub)}</dd>
        </div>
      </dl>
    </div>
  );
}

function Steps({ steps }: { steps: TraceStep[] }) {
  const headingId = useId();
  return (
    <section className="card trace-card" aria-labelledby={headingId}>
      <h2 id={headingId}>Шаги</h2>
      <ol className="trace-steps">
        {steps.map((step, index) => (
          <li key={index} className="trace-step" data-failed={step.step === "final" && step.name === FAILED}>
            <details>
              <summary>
                <span className="trace-step-name">{stepLabel(step)}</span>
                <span className="trace-step-meta">{stepMeta(step)}</span>
              </summary>
              <dl>
                <dt>Аргументы</dt>
                <dd>{step.input_summary || "—"}</dd>
                <dt>Результат</dt>
                <dd>
                  <pre className="trace-raw">{step.output_summary}</pre>
                </dd>
              </dl>
            </details>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Verdicts({ verdicts }: { verdicts: string[] }) {
  const headingId = useId();
  return (
    <section className="card trace-card" aria-labelledby={headingId}>
      <h2 id={headingId}>Проверка критика</h2>
      <ul className="icon-list">
        {verdicts.map(verdictLabel).map(({ text, ok }, index) => (
          <li key={index} data-ok={ok}>
            <span className={ok ? "check-mark" : "check-mark check-mark-issue"} aria-hidden="true">
              <Icon name={ok ? "check" : "alert"} size={16} />
            </span>
            {text}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Result({ request, response }: { request: InterpretRequest; response: InterpretResponse }) {
  const headingId = useId();
  return (
    <section className="trace-result" aria-labelledby={headingId}>
      <h2 id={headingId}>Итог</h2>
      <Panel actionContext={request.action_context} role={request.role} response={response} />
    </section>
  );
}

function TraceView({ trace }: { trace: Trace }) {
  return (
    <div className="trace-layout">
      <Summary trace={trace} />
      <Steps steps={trace.steps} />
      {trace.critic_verdicts.length > 0 && <Verdicts verdicts={trace.critic_verdicts} />}
      {trace.result && <Result request={trace.request} response={trace.result} />}
    </div>
  );
}

function Failure({ error }: { error: unknown }) {
  if (error instanceof ApiError && MISSING.has(error.status)) {
    return (
      <div className="card trace-card">
        <p className="empty">
          Трасса не найдена. <Link to="/">На главную</Link>
        </p>
      </div>
    );
  }
  return <Alert text="Не удалось загрузить трассу" />;
}

export function TracePage() {
  const { id = "" } = useParams();
  const [trace] = useLoad(useCallback(() => api.trace(id), [id]));
  return (
    <section>
      <div className="page-head">
        <Link to="/" className="page-back">
          ← Главная
        </Link>
        <h1>Как получен вывод</h1>
        {trace.status === "ready" && (
          <p className="page-sub">
            {requestLabel(trace.value.request)} · {WHEN.format(new Date(trace.value.created_at))}
          </p>
        )}
      </div>
      {trace.status === "loading" && (
        <div className="card trace-card" aria-busy="true">
          <Skeleton text="Загружаю трассу" />
        </div>
      )}
      {trace.status === "failed" && <Failure error={trace.error} />}
      {trace.status === "ready" && <TraceView trace={trace.value} />}
    </section>
  );
}
