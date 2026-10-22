import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { Icon } from "./Icon";
import { matchIndex, moveIndex } from "./listbox";

export interface SelectOption {
  value: string;
  label: string;
  hint?: string;
  mark?: string;
}

interface SelectProps {
  label: string;
  value: string;
  options: readonly SelectOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  variant?: "field" | "pill";
  describedBy?: string;
}

const TYPEAHEAD_RESET_MS = 600;
const OPENING_KEYS = new Set(["ArrowDown", "ArrowUp", "Enter", " "]);

function Mark({ text }: { text: string }) {
  return (
    <span className="company-mark" aria-hidden="true">
      {text}
    </span>
  );
}

export function Select({
  label,
  value,
  options,
  onChange,
  placeholder = "",
  variant = "field",
  describedBy,
}: SelectProps) {
  const id = useId();
  const labelId = `${id}-label`;
  const listId = `${id}-list`;
  const root = useRef<HTMLDivElement>(null);
  const typed = useRef({ query: "", at: 0 });
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const selectedIndex = options.findIndex((option) => option.value === value);
  const selected = options[selectedIndex];
  const optionId = (index: number) => `${id}-option-${index}`;

  useEffect(() => {
    if (!open) {
      return;
    }
    const closeOutside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", closeOutside);
    return () => document.removeEventListener("mousedown", closeOutside);
  }, [open]);

  useEffect(() => {
    if (open && active >= 0) {
      document.getElementById(optionId(active))?.scrollIntoView?.({ block: "nearest" });
    }
  });

  function show(index: number) {
    setActive(index);
    setOpen(true);
  }

  function choose(index: number) {
    setOpen(false);
    if (index >= 0 && options[index].value !== value) {
      onChange(options[index].value);
    }
  }

  function typeahead(char: string) {
    const now = Date.now();
    const query = now - typed.current.at > TYPEAHEAD_RESET_MS ? char : typed.current.query + char;
    typed.current = { query, at: now };
    const found = matchIndex(
      options.map((option) => option.label),
      query,
      open ? active : selectedIndex,
    );
    if (found >= 0) {
      show(found);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const { key } = event;
    if (key.length === 1 && key !== " " && !event.ctrlKey && !event.metaKey && !event.altKey) {
      event.preventDefault();
      typeahead(key);
      return;
    }
    if (!open) {
      if (OPENING_KEYS.has(key) || key === "Home" || key === "End") {
        event.preventDefault();
        const start = key === "End" ? options.length - 1 : key === "Home" ? 0 : Math.max(selectedIndex, 0);
        show(start);
      }
      return;
    }
    if (key === "Escape") {
      event.preventDefault();
      setOpen(false);
    } else if (key === "Enter" || key === " " || (key === "ArrowUp" && event.altKey)) {
      event.preventDefault();
      choose(active);
    } else if (key === "Tab") {
      choose(active);
    } else {
      const next = moveIndex(key, active, options.length);
      if (next !== null) {
        event.preventDefault();
        setActive(next);
      }
    }
  }

  return (
    <div ref={root} className={`select select-${variant}`} data-open={open}>
      <span id={labelId} className={variant === "field" ? "select-label" : "visually-hidden"}>
        {label}
      </span>
      <button
        type="button"
        role="combobox"
        className="select-trigger"
        aria-labelledby={labelId}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={open && active >= 0 ? optionId(active) : undefined}
        aria-describedby={describedBy}
        onClick={() => (open ? setOpen(false) : show(Math.max(selectedIndex, 0)))}
        onKeyDown={onKeyDown}
      >
        {variant === "pill" && selected?.mark && <Mark text={selected.mark} />}
        <span className={selected ? "select-value" : "select-value select-placeholder"}>
          {selected ? selected.label : placeholder}
        </span>
        <Icon name="chevron-down" size={18} className="select-chevron" />
      </button>
      {open && (
        <ul id={listId} role="listbox" aria-labelledby={labelId} className="select-list" tabIndex={-1}>
          {options.map((option, index) => (
            <li
              key={option.value}
              id={optionId(index)}
              role="option"
              aria-selected={option.value === value}
              className={index === active ? "select-option is-active" : "select-option"}
              onMouseDown={(event) => event.preventDefault()}
              onMouseMove={() => setActive(index)}
              onClick={() => choose(index)}
            >
              {option.mark && <Mark text={option.mark} />}
              <span className="select-option-text">
                <span>{option.label}</span>
                {option.hint && <span className="select-hint">{option.hint}</span>}
              </span>
              {option.value === value && <Icon name="check" size={18} className="select-check" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
