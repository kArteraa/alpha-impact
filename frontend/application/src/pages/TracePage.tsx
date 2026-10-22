import type { Trace, TraceStep } from "@alpha-impact/plugin";
import { useId } from "react";
import { Link, useParams } from "react-router";
import { TRACES } from "../data/trace";
import { NUMBER } from "../money";
import { type StepKind, traceSummary } from "../trace/summary";
import { ShareBar } from "../ui/charts/ShareBar";
import type { Tone } from "../ui/charts/tone";
import { Icon } from "../ui/Icon";

const SECONDS = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const WHEN = new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short", timeZone: "Europe/Moscow" });
const MS_IN_SECOND = 1000;

const PARTS: Record<StepKind, readonly [string, Tone]> = {
  model: ["Модели", "ai"],
  tool: ["Поиск новостей и позиции банка", "bank"],
  service: ["Служебные шаги", "soft"],
};

function stepMeta(step: TraceStep): string {
  const parts: string[] = [];
  if (step.duration_ms !== undefined) {
    parts.push(`${NUMBER.format(step.duration_ms)} мс`);
  }
  if (step.tokens_in !== undefined && step.tokens_out !== undefined) {
    parts.push(`${NUMBER.format(step.tokens_in)} → ${NUMBER.format(step.tokens_out)} токенов`);
  }
  if (step.model) {
    parts.push(step.model);
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
      </dl>
    </div>
  );
}

function Verdicts({ verdicts }: { verdicts: string[] }) {
  const headingId = useId();
  return (
    <section className="card trace-card" aria-labelledby={headingId}>
      <h2 id={headingId}>Проверка критика</h2>
      <ul className="verdicts">
        {verdicts.map((verdict) => (
          <li key={verdict}>
            <span className="verdict-mark" aria-hidden="true">
              <Icon name="check" size={16} />
            </span>
            {verdict}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function TracePage() {
  const { id = "" } = useParams();
  const stepsId = useId();
  const trace = Object.hasOwn(TRACES, id) ? TRACES[id] : undefined;
  return (
    <section>
      <div className="page-head">
        <Link to="/" className="page-back">
          ← Главная
        </Link>
        <h1>Как получен вывод</h1>
        <p className="page-sub">
          Трасса {id}
          {trace && <> · {WHEN.format(new Date(trace.created_at))}</>}
        </p>
      </div>
      {trace === undefined ? (
        <div className="card trace-card">
          <p className="empty">
            Трасса не найдена. <Link to="/">На главную</Link>
          </p>
        </div>
      ) : (
        <div className="trace-layout">
          <Summary trace={trace} />
          <section className="card trace-card" aria-labelledby={stepsId}>
            <h2 id={stepsId}>Шаги</h2>
            <ol className="trace-steps">
              {trace.steps.map((step) => (
                <li key={step.started_at} className="trace-step">
                  <details>
                    <summary>
                      <span className="trace-step-name">{step.name}</span>
                      <span className="trace-step-meta">{stepMeta(step)}</span>
                    </summary>
                    <dl>
                      <dt>На входе</dt>
                      <dd>{step.input_summary}</dd>
                      <dt>Результат</dt>
                      <dd>{step.output_summary}</dd>
                    </dl>
                  </details>
                </li>
              ))}
            </ol>
          </section>
          {trace.critic_verdicts.length > 0 && <Verdicts verdicts={trace.critic_verdicts} />}
        </div>
      )}
    </section>
  );
}
