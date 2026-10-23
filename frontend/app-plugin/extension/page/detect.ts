import {
  ARTICLE_MIN_CHARS,
  FX_CURRENCY_CODES,
  PAGE_DOMAINS,
  PAGE_TEXT_MAX_CHARS,
  type PageType,
  TENDER_SUBJECT_LABELS,
} from "../config";
import type { DetectedPage } from "../messages";
import { innsIn } from "./inn";
import { heading, paragraphs, textLines } from "./text";

const PURCHASE_NUMBER = /№\s*(\d{11,19})(?!\d)/;
const CURRENCY = new RegExp(`\\b(?:${FX_CURRENCY_CODES.join("|")})\\b`);
const SUBJECT_LINE = new RegExp(`^(?:${TENDER_SUBJECT_LABELS.join("|")})\\s*(?::\\s*(.*))?$`);
const PAGE_TYPES = Object.keys(PAGE_DOMAINS) as PageType[];

interface Extracted {
  lines: string[];
  entities?: string[];
}

type Rule = (body: HTMLElement) => Extracted | null;

function pageTypeOf(hostname: string): PageType | undefined {
  return PAGE_TYPES.find((type) =>
    PAGE_DOMAINS[type].some((domain) => hostname === domain || hostname === `www.${domain}`),
  );
}

function headed(body: HTMLElement): Extracted | null {
  const title = heading(body);
  return title === "" ? null : { lines: [title, ...textLines(body).filter((line) => line !== title)] };
}

function article(body: HTMLElement): Extracted | null {
  const title = heading(body);
  const text = paragraphs(body);
  const length = text.reduce((sum, line) => sum + line.length, 0);
  return title !== "" && length >= ARTICLE_MIN_CHARS ? { lines: [title, ...text] } : null;
}

function counterparty(body: HTMLElement): Extracted | null {
  const page = headed(body);
  if (page === null) {
    return null;
  }
  const [inn] = innsIn(page.lines.join("\n"));
  return inn === undefined ? null : { ...page, entities: [`inn:${inn}`] };
}

function subjectOf(lines: string[]): string | undefined {
  for (const [index, line] of lines.entries()) {
    const match = SUBJECT_LINE.exec(line);
    if (match !== null) {
      return match[1] || lines[index + 1];
    }
  }
  return undefined;
}

function tender(body: HTMLElement): Extracted | null {
  const lines = textLines(body);
  const number = PURCHASE_NUMBER.exec(lines.join("\n"))?.[1];
  const subject = subjectOf(lines);
  if (number === undefined || subject === undefined) {
    return null;
  }
  return { lines: [subject, `Закупка № ${number}`, ...lines.filter((line) => line !== subject)] };
}

function fxRate(body: HTMLElement): Extracted | null {
  const page = headed(body);
  return page !== null && CURRENCY.test(page.lines.join("\n")) ? page : null;
}

const RULES: Record<PageType, Rule> = { article, counterparty, tender, fx_rate: fxRate };

export function detectPage(document: Document, url: string): DetectedPage | null {
  const address = new URL(url);
  address.hash = "";
  const pageType = pageTypeOf(address.hostname);
  if (pageType === undefined || document.body === null) {
    return null;
  }
  const extracted = RULES[pageType](document.body);
  if (extracted === null) {
    return null;
  }
  const text = extracted.lines.join("\n").slice(0, PAGE_TEXT_MAX_CHARS);
  return { pageType, page: { type: "page", url: address.href, text, entities: extracted.entities ?? [] } };
}
