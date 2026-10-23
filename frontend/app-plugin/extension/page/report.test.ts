import { within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import controls from "../../src/styles/controls.css?raw";
import tokens from "../../src/styles/tokens.css?raw";
import type { Send, WorkerRequest } from "../messages";
import { reportPage } from "./report";

const COMPANY_URL = "https://www.rusprofile.ru/id/123";

function counterparty(): Document {
  return new DOMParser().parseFromString("<h1>ООО «ТрансЛогистик»</h1><p>ИНН 7707083893</p>", "text/html");
}

function notice(document: Document): ShadowRoot | null {
  return document.querySelector("alpha-impact-notice")?.shadowRoot ?? null;
}

function button(root: ShadowRoot, name: string): HTMLElement {
  return within(root.querySelector<HTMLElement>(".notice")!).getByRole("button", { name });
}

async function reported(offer: boolean, url = COMPANY_URL) {
  const document = counterparty();
  const send = vi.fn(async (_request: WorkerRequest) => offer);
  const openPanel = vi.fn();
  await reportPage(document, url, send as unknown as Send, openPanel);
  return { document, send, openPanel };
}

describe("reportPage", () => {
  it("reports the detected page to the worker", async () => {
    const { send } = await reported(false);

    expect(send).toHaveBeenCalledWith({
      type: "page",
      detected: expect.objectContaining({ pageType: "counterparty", page: expect.objectContaining({ url: COMPANY_URL }) }),
    });
  });

  it("does not wake the worker on an unrecognised page", async () => {
    const { document, send } = await reported(true, "https://example.com/company");

    expect(send).not.toHaveBeenCalled();
    expect(notice(document)).toBeNull();
  });

  it("shows nothing when the worker does not offer the notice", async () => {
    const { document } = await reported(false);

    expect(notice(document)).toBeNull();
  });

  it("tells about an event for the company when the worker offers it", async () => {
    const { document } = await reported(true);

    expect(notice(document)?.querySelector('[role="status"]')?.textContent).toContain(
      "есть событие, важное для вашей компании",
    );
  });

  it("opens the panel and goes away on «Открыть»", async () => {
    const { document, openPanel } = await reported(true);

    button(notice(document)!, "Открыть").click();

    expect(openPanel).toHaveBeenCalledOnce();
    expect(notice(document)).toBeNull();
  });

  it("goes away on close without opening the panel", async () => {
    const { document, openPanel } = await reported(true);

    button(notice(document)!, "Закрыть").click();

    expect(openPanel).not.toHaveBeenCalled();
    expect(notice(document)).toBeNull();
  });

  it("takes the design tokens into its shadow root", async () => {
    const { document } = await reported(true);

    const style = notice(document)?.querySelector("style")?.textContent ?? "";
    expect(style).toContain(tokens);
    expect(style).toContain(controls);
  });
});
