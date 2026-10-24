import { type HTMLAttributes, type ReactNode, useContext } from "react";
import type { SourceRef } from "../types";
import { ApiBaseContext } from "./apiBase";

interface SourceLinkProps extends HTMLAttributes<HTMLElement> {
  source: SourceRef;
  children: ReactNode;
}

const SAFE_URL = /^https?:\/\//i;
const GATEWAY_PATH = /^\/(?![/\\])[^\u0000- \u007f]*$/;

function sourceHref({ kind, url }: SourceRef, apiBase: string | undefined): string | null {
  if (!url) {
    return null;
  }
  if (SAFE_URL.test(url)) {
    return url;
  }
  return kind === "house_view" && apiBase && GATEWAY_PATH.test(url) ? `${apiBase}${url}` : null;
}

export function SourceLink({ source, children, ...attributes }: SourceLinkProps) {
  const href = sourceHref(source, useContext(ApiBaseContext));
  if (href) {
    return (
      <a href={href} target="_blank" rel="noreferrer" {...attributes}>
        {children}
      </a>
    );
  }
  return (
    <span role={attributes["aria-label"] ? "img" : undefined} {...attributes}>
      {children}
    </span>
  );
}
