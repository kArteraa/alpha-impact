import type { SourceRef } from "../types";
import { SOURCE_KINDS, sourceTitle } from "./labels";

function SourceTitle({ source }: { source: SourceRef }) {
  const title = sourceTitle(source);
  if (source.url) {
    return (
      <a href={source.url} target="_blank" rel="noreferrer">
        {title}
      </a>
    );
  }
  return <span>{title}</span>;
}

export function SourceList({ sources }: { sources: SourceRef[] }) {
  return (
    <ul className="sources">
      {sources.map((source) => {
        const kind = SOURCE_KINDS[source.kind];
        return (
          <li key={source.id}>
            <span className="source-icon" role="img" aria-label={kind.label} title={kind.label}>
              {kind.icon}
            </span>
            <SourceTitle source={source} />
          </li>
        );
      })}
    </ul>
  );
}
