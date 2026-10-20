import { type ReactNode, useId } from "react";

interface BlockProps {
  title: string;
  collapsible: boolean;
  className?: string;
  children: ReactNode;
}

export function Block({ title, collapsible, className = "", children }: BlockProps) {
  const headingId = useId();
  const heading = <h4 id={headingId}>{title}</h4>;
  if (collapsible) {
    return (
      <details className={`block ${className}`}>
        <summary>{heading}</summary>
        {children}
      </details>
    );
  }
  return (
    <section className={`block ${className}`} aria-labelledby={headingId}>
      {heading}
      {children}
    </section>
  );
}
