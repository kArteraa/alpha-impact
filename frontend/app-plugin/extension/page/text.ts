const SKIPPED = 'script, style, noscript, template, nav, footer, aside, [hidden], [aria-hidden="true"]';

function collapse(text: string | null | undefined): string {
  return (text ?? "").replace(/\s+/g, " ").trim();
}

function shownText(node: Node): number {
  if (node instanceof Element) {
    return node.matches(SKIPPED) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_SKIP;
  }
  return NodeFilter.FILTER_ACCEPT;
}

export function textLines(root: Element): string[] {
  const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
    acceptNode: shownText,
  });
  const lines: string[] = [];
  for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
    const line = collapse(node.textContent);
    if (line !== "") {
      lines.push(line);
    }
  }
  return lines;
}

export function paragraphs(root: Element): string[] {
  return Array.from(root.querySelectorAll("p"))
    .filter((paragraph) => paragraph.closest(SKIPPED) === null)
    .map((paragraph) => collapse(paragraph.textContent))
    .filter((line) => line !== "");
}

export function heading(root: Element): string {
  const shown = Array.from(root.querySelectorAll("h1")).find((element) => element.closest(SKIPPED) === null);
  return collapse(shown?.textContent);
}
