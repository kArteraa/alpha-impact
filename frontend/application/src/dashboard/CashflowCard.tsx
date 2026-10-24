import { useId } from "react";
import { useCompany } from "../company/context";
import { CASHFLOW } from "../data/cashflow";
import { RUB_COMPACT } from "../money";
import { Columns, type ColumnSeries } from "../ui/charts/Columns";
import { plural } from "../ui/plural";

const WEEKS = { one: "неделя", few: "недели", many: "недель" };

const WEEK = new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit", timeZone: "UTC" });

const SERIES: readonly ColumnSeries[] = [
  { name: "Поступления", tone: "primary" },
  { name: "Списания", tone: "muted" },
];

export function CashflowCard() {
  const { company } = useCompany();
  const headingId = useId();
  const weeks = CASHFLOW[company.id];
  if (!weeks) {
    return null;
  }
  const rows = weeks.map((week) => [week.inflow, week.outflow]);
  const totals = SERIES.map((_, index) => rows.reduce((sum, row) => sum + row[index], 0));
  return (
    <section className="card cashflow" aria-labelledby={headingId}>
      <div className="cashflow-head">
        <h2 id={headingId}>Движение денег</h2>
        <span className="muted">{plural(weeks.length, WEEKS)} · демо-данные</span>
      </div>
      <dl className="cashflow-totals">
        {SERIES.map((series, index) => (
          <div key={series.name}>
            <dt>
              <span className="share-dot" data-tone={series.tone} aria-hidden="true" />
              {series.name}
            </dt>
            <dd>{RUB_COMPACT.format(totals[index])}</dd>
          </div>
        ))}
      </dl>
      <Columns
        title="Поступления и списания по неделям, с понедельника"
        series={SERIES}
        groups={weeks.map((week, index) => ({ label: WEEK.format(new Date(week.start)), values: rows[index] }))}
        format={(value) => RUB_COMPACT.format(value)}
      />
    </section>
  );
}
