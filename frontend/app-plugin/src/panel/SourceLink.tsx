import type { HTMLAttributes, ReactNode } from "react";
import type { SourceRef } from "../types";

interface SourceLinkProps extends HTMLAttributes<HTMLElement> {
  source: SourceRef;
  children: ReactNode;
}

const SAFE_URL = /^https?:\/\//i;

export function SourceLink({ source, children, ...attributes }: SourceLinkProps) {
  if (source.url && SAFE_URL.test(source.url)) {
    return (
      <a href={source.url} target="_blank" rel="noreferrer" {...attributes}>
        {children}
      </a>
    );
  }
  return <span {...attributes}>{children}</span>;
}
