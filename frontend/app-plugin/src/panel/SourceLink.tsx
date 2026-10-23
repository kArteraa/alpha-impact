import { type HTMLAttributes, type ReactNode, useContext } from "react";
import type { SourceRef } from "../types";
import { ApiBaseContext } from "./apiBase";

interface SourceLinkProps extends HTMLAttributes<HTMLElement> {
  source: SourceRef;
  children: ReactNode;
}

const SAFE_URL = /^https?:\/\//i;
const GATEWAY_PATH = /^\/(?!\/)/;

function sourceHref(url: string | null | undefined, apiBase: string | undefined): string | null {
  if (!url) {
    return null;
  }
  if (SAFE_URL.test(url)) {
    return url;
  }
  return apiBase !== undefined && GATEWAY_PATH.test(url) ? `${apiBase}${url}` : null;
}

export function SourceLink({ source, children, ...attributes }: SourceLinkProps) {
  const href = sourceHref(source.url, useContext(ApiBaseContext));
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
