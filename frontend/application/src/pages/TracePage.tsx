import type { TraceStep } from "@alpha-impact/plugin";
import { Link, useParams } from "react-router";
import { TRACES } from "../data/trace";

const NUMBER = new Intl.NumberFormat("ru-RU");

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

export function TracePage() {
  const { id = "" } = useParams();
  const trace = TRACES[id];
  return (
    <section>
      <h1>Трасса {id}</h1>
      <div className="card">
        {trace === undefined ? (
          <p className="empty">
            Трасса не найдена. <Link to="/">На главную</Link>
          </p>
        ) : (
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
        )}
      </div>
    </section>
  );
}
