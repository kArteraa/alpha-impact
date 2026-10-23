import type { InterpretState } from "@alpha-impact/plugin";
import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { panelState, renderWithCompany } from "../testing";
import { EventPage } from "./EventPage";

function renderEvent(id: string, feed: Partial<InterpretState> = {}) {
  return renderWithCompany(<EventPage />, { path: "/events/:id", entry: `/events/${id}`, feed });
}

describe("EventPage", () => {
  afterEach(cleanup);

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

  it("says so when the event is no longer in the feed", () => {
    renderEvent("ev-gone");

    expect(screen.getByRole("heading", { name: "Событие больше не в ленте" })).toBeTruthy();
    expect(panelState()).toBeUndefined();
  });

  it("shows that it is still looking for events", () => {
    renderEvent("ev-rate", { response: undefined });

    expect(screen.getByText("Смотрю новости и позицию банка за 14 дней")).toBeTruthy();
  });
});
