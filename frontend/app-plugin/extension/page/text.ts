const SKIPPED = "script, style, noscript, template, nav, footer, aside";

function collapse(text: string | null): string {
  return (text ?? "").replace(/\s+/g, " ").trim();
}

function shown(element: Element | null): boolean {
  return element !== null && element.closest(SKIPPED) === null;
}

export function textLines(root: Element): string[] {
  const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const lines: string[] = [];
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    const line = collapse(node.textContent);
    if (line !== "" && shown(node.parentElement)) {
      lines.push(line);
    }
  }
  return lines;
}

export function paragraphs(root: Element): string[] {
  return Array.from(root.querySelectorAll("p"))
    .filter(shown)
    .map((paragraph) => collapse(paragraph.textContent))
    .filter((line) => line !== "");
}

export function heading(root: Element): string {
  return collapse(root.querySelector("h1")?.textContent ?? null);
}
