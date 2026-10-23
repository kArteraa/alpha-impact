import type { InterpretState } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { panelState, renderWithCompany, stubApi } from "../testing";
import { EventPage } from "./EventPage";

function renderEvent(id: string, feed: Partial<InterpretState> = {}) {
  return renderWithCompany(<EventPage />, { path: "/events/:id", entry: `/events/${id}`, feed });
}

describe("EventPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the full card of the event from the feed", () => {
    renderEvent("ev-rate");

    expect(panelState()).toBe("cards");
    expect(document.querySelectorAll(".insight-card")).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 3, name: "Банк ждёт снижения ключевой ставки" })).toBeTruthy();
    expect(document.querySelector(".insight-card")?.textContent).toContain(
      "Платёж по кредитной линии с плавающей ставкой снизится",
    );
    expect(screen.getByRole("link", { name: "Все события" }).getAttribute("href")).toBe("/events");
  });

  it("leads the bank source of the event to the page of the report", () => {
    renderEvent("ev-rate");

    expect(screen.getByLabelText(/^Банк — источник: /).getAttribute("href")).toBe("/api/reports/ALFA-7M26.pdf#page=1");
  });

  it("sends feedback on the event", async () => {
    const fetchMock = stubApi({ "POST /api/feedback": [204, null] });
    renderEvent("ev-rate");

    fireEvent.click(screen.getByRole("button", { name: "Не полезно" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Не полезно" }).getAttribute("aria-pressed")).toBe("true"),
    );
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/feedback");
    expect(JSON.parse(String(init?.body))).toEqual({ card_id: "ev-rate", useful: false });
  });

  it("says so when the event is no longer in the feed", () => {
    renderEvent("ev-gone");

    expect(screen.getByRole("heading", { name: "Событие больше не в ленте" })).toBeTruthy();
    expect(panelState()).toBeUndefined();
  });

  it("shows that it is still looking for events", () => {
    renderEvent("ev-rate", { response: undefined });

    expect(screen.getByText("Смотрю новости и позицию банка")).toBeTruthy();
  });
});
