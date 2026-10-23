import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { renderWithCompany } from "../testing";
import { EventsPage } from "./EventsPage";

describe("EventsPage", () => {
  afterEach(cleanup);

  it("lists every event of the company by significance", () => {
    renderWithCompany(<EventsPage />, { path: "/events" });

    const headlines = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headlines).toEqual([
      "Логистика в убытке",
      "Банк ждёт снижения ключевой ставки",
      "Юань дорожает к рублю",
      "Розничный спрос в регионах замедлился",
    ]);
    expect(screen.getAllByLabelText(/^Значимость \d из 3$/).length).toBe(4);
  });

  it("groups the events by significance with a count", () => {
    renderWithCompany(<EventsPage />, { path: "/events" });

    const groups = screen.getAllByRole("region").map((group) => [
      group.querySelector("h2")?.textContent,
      group.querySelector(".badge")?.textContent,
    ]);
    expect(groups).toEqual([
      ["Высокая значимость", "2"],
      ["Средняя значимость", "2"],
    ]);
  });

  it("names the company under the heading", () => {
    renderWithCompany(<EventsPage />, { path: "/events" });

    expect(screen.getByText("ООО «Северный опт»")).toBeTruthy();
  });
});
