import { shares } from "./scale";
import type { Tone } from "./tone";

export interface Share {
  label: string;
  value: number;
  tone: Tone;
  caption: string;
}

export function ShareBar({ items, label }: { items: readonly Share[]; label: string }) {
  const percents = shares(items.map((item) => item.value));
  return (
    <div className="share-bar">
      <span className="share-track" aria-hidden="true">
        {items.map((item, index) => (
          <span
            key={item.label}
            className="share-part"
            data-tone={item.tone}
            style={{ width: `${percents[index]}%` }}
          />
        ))}
      </span>
      <ul className="share-legend" aria-label={label}>
        {items.map((item) => (
          <li key={item.label}>
            <span className="share-dot" data-tone={item.tone} aria-hidden="true" />
            <span className="share-name">{item.label}</span>
            <span className="share-caption">{item.caption}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
