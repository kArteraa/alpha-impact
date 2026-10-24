import type { SourceRef } from "../types";
import { SOURCE_KINDS, sourceTitle } from "./labels";
import { SourceLink } from "./SourceLink";

function shown(sources: SourceRef[]): SourceRef[] {
  const seen = new Set<string>();
  return sources.filter((source) => {
    const key = [source.kind, sourceTitle(source), source.url].join("|");
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

export function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <ul className="insight-sources">
      {shown(sources).map((source) => {
        const kind = SOURCE_KINDS[source.kind];
        return (
          <li key={source.id}>
            <span className="source-icon" role="img" aria-label={kind.label} title={kind.label}>
              {kind.icon}
            </span>
            <SourceLink source={source}>{sourceTitle(source)}</SourceLink>
          </li>
        );
      })}
    </ul>
  );
}
