const PAGE = 10;
const LEGAL_FORM = /^(ООО|АО|ПАО|ЗАО|ИП)\s+/;

export function stripLegalForm(name: string): string {
  return name.replace(LEGAL_FORM, "").replace(/[«»"]/g, "").trim();
}

export function moveIndex(key: string, current: number, count: number): number | null {
  const last = count - 1;
  switch (key) {
    case "ArrowDown":
      return Math.min(current + 1, last);
    case "ArrowUp":
      return Math.max(current - 1, 0);
    case "Home":
      return 0;
    case "End":
      return last;
    case "PageDown":
      return Math.min(Math.max(current, 0) + PAGE, last);
    case "PageUp":
      return Math.max(current - PAGE, 0);
    default:
      return null;
  }
}

function matches(label: string, query: string): boolean {
  const lower = query.toLowerCase();
  return label.toLowerCase().startsWith(lower) || stripLegalForm(label).toLowerCase().startsWith(lower);
}

export function matchIndex(labels: readonly string[], query: string, current: number): number {
  const start = query.length === 1 ? current + 1 : Math.max(current, 0);
  for (let offset = 0; offset < labels.length; offset += 1) {
    const index = (start + offset) % labels.length;
    if (matches(labels[index], query)) {
      return index;
    }
  }
  return -1;
}
