import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { renderWithCompany } from "../testing";
import { EventsPage } from "./EventsPage";

describe("EventsPage", () => {
  afterEach(cleanup);

  it("lists every event of the company by significance", () => {
    renderWithCompany(<EventsPage />, "/events");

    const headlines = screen.getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headlines).toEqual([
      "Логистика в убытке",
      "Банк ждёт снижения ключевой ставки",
      "Юань дорожает к рублю",
      "Розничный спрос в регионах замедлился",
    ]);
    expect(screen.getAllByLabelText(/^Значимость \d из 3$/).length).toBe(4);
  });

  it("names the company under the heading", () => {
    renderWithCompany(<EventsPage />, "/events");

    expect(screen.getByText("ООО «Северный опт»")).toBeTruthy();
  });
});
