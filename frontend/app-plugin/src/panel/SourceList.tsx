import type { SourceRef } from "../types";
import { SOURCE_KINDS, sourceTitle } from "./labels";
import { SourceLink } from "./SourceLink";

export function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <ul className="insight-sources">
      {sources.map((source) => {
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
