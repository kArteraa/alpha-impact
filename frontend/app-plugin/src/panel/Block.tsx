import { type ReactNode, useId } from "react";

interface BlockProps {
  title: string;
  collapsible: boolean;
  className?: string;
  children: ReactNode;
}

export function Block({ title, collapsible, className, children }: BlockProps) {
  const headingId = useId();
  const classes = className ? `insight-block ${className}` : "insight-block";
  const heading = <h4 id={headingId}>{title}</h4>;
  if (collapsible) {
    return (
      <details className={classes}>
        <summary>{heading}</summary>
        {children}
      </details>
    );
  }
  return (
    <section className={classes} aria-labelledby={headingId}>
      {heading}
      {children}
    </section>
  );
}
