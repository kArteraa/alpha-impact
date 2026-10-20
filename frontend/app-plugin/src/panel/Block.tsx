import { type ReactNode, useId, useState } from "react";

interface BlockProps {
  title: string;
  collapsible: boolean;
  className?: string;
  children: ReactNode;
}

export function Block({ title, collapsible, className, children }: BlockProps) {
  const headingId = useId();
  const contentId = useId();
  const [open, setOpen] = useState(false);
  const classes = className ? `insight-block ${className}` : "insight-block";
  if (collapsible) {
    return (
      <section className={classes} aria-labelledby={headingId}>
        <h4 id={headingId}>
          <button
            type="button"
            className="insight-block-toggle"
            aria-expanded={open}
            aria-controls={contentId}
            onClick={() => setOpen((current) => !current)}
          >
            {title}
          </button>
        </h4>
        {open && <div id={contentId}>{children}</div>}
      </section>
    );
  }
  return (
    <section className={classes} aria-labelledby={headingId}>
      <h4 id={headingId}>{title}</h4>
      {children}
    </section>
  );
}
