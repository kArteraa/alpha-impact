import { ratio } from "./scale";
import type { Tone } from "./tone";

const MIN_BAR_PERCENT = 2;

export interface ColumnSeries {
  name: string;
  tone: Tone;
}

interface ColumnGroup {
  label: string;
  values: readonly number[];
  active?: boolean;
}

interface ColumnsProps {
  title: string;
  series: readonly ColumnSeries[];
  groups: readonly ColumnGroup[];
  format: (value: number) => string;
  showValues?: boolean;
}

export function Columns({ title, series, groups, format, showValues = false }: ColumnsProps) {
  const max = Math.max(...groups.flatMap((group) => group.values));
  return (
    <div className="columns">
      <div className="visually-hidden">
        <table>
          <caption>{title}</caption>
          <thead>
            <tr>
              <th scope="col">Период</th>
              {series.map((item) => (
                <th key={item.name} scope="col">
                  {item.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <tr key={group.label}>
                <th scope="row">{group.label}</th>
                {group.values.map((value, index) => (
                  <td key={series[index].name}>{format(value)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="columns-plot" aria-hidden="true">
        {groups.map((group) => (
          <div key={group.label} className="columns-group" data-active={group.active ?? false}>
            {showValues && <span className="columns-caption">{group.values.map(format).join(" · ")}</span>}
            <span className="columns-bars">
              {group.values.map((value, index) => (
                <span
                  key={series[index].name}
                  className="columns-bar"
                  data-tone={series[index].tone}
                  style={{ height: `${value > 0 ? Math.max(ratio(value, max) * 100, MIN_BAR_PERCENT) : 0}%` }}
                />
              ))}
            </span>
            <span className="columns-label">{group.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
