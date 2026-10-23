import type { InterpretState } from "@alpha-impact/plugin";
import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { SILENT_FEED, feedOf } from "../dashboard/events.fixture";
import { TEST_CLIENT, renderWithCompany } from "../testing";
import { EventsPage } from "./EventsPage";

function renderEvents(feed: Partial<InterpretState> = { response: feedOf(TEST_CLIENT) }) {
  return renderWithCompany(<EventsPage />, { path: "/events", feed });
}

describe("EventsPage", () => {
  afterEach(cleanup);

  it("lists every event of the feed in its ranked order", () => {
    renderEvents();

    const headlines = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headlines).toEqual([
      "Логистика в убытке",
      "Банк ждёт снижения ключевой ставки",
      "Юань дорожает к рублю",
      "Розничный спрос в регионах замедлился",
    ]);
    expect(screen.getAllByLabelText(/^Значимость \d из 3$/).length).toBe(4);
    expect(screen.getByRole("link", { name: "Юань дорожает к рублю" }).getAttribute("href")).toBe("/events/ev-yuan");
  });

  it("groups the events by significance with a count", () => {
    renderEvents();

    const groups = screen.getAllByRole("region").map((group) => [
      group.querySelector("h2")?.textContent,
      group.querySelector(".badge")?.textContent,
    ]);
    expect(groups).toEqual([
      ["Высокая значимость", "2"],
      ["Средняя значимость", "2"],
    ]);
  });

  it("names the company and the number of events under the heading", () => {
    renderEvents();

    expect(document.querySelector(".page-sub")?.textContent).toBe("ООО «Северный опт» · 4 события");
  });

  it("shows that it is still looking for events", () => {
    renderEvents({});

    expect(screen.getByText("Смотрю новости и позицию банка за 14 дней")).toBeTruthy();
    expect(document.querySelector(".page-sub")?.textContent).toBe("ООО «Северный опт»");
  });

  it("says so explicitly when nothing important happened", () => {
    renderEvents({ response: SILENT_FEED });

    expect(screen.getByRole("status").textContent).toContain("Пока ничего важного");
    expect(screen.getByRole("link", { name: "Проверить профиль компании" }).getAttribute("href")).toBe("/profile");
  });
});
