import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { TracePage } from "./TracePage";

function renderTrace(id: string) {
  render(
    <MemoryRouter initialEntries={[`/trace/${id}`]}>
      <Routes>
        <Route path="/trace/:id" element={<TracePage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("TracePage", () => {
  afterEach(cleanup);

  it("reads as a journal of steps", () => {
    renderTrace("trace-mock-1");

    const steps = Array.from(document.querySelectorAll(".trace-step-name"), (step) => step.textContent);
    expect(steps).toEqual(["Предфильтр", "План", "Поиск новостей и позиции банка", "Черновик", "Критик", "Итог"]);
    expect(screen.getByText(/1 240 → 180 токенов/)).toBeTruthy();
    expect(screen.getByText(/820 мс/)).toBeTruthy();
  });

  it("sums up the time, the tokens and the models", () => {
    renderTrace("trace-mock-1");

    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Как получен вывод");
    expect(screen.getByText("3,5 с")).toBeTruthy();
    const facts = document.querySelector(".trace-facts")?.textContent?.replace(/\s/g, " ");
    expect(facts).toBe("Токены5 830 → 790МоделиQwen3.6 35B A3B, GLM-5.3-FlashШагов6");
    const parts = Array.from(
      screen.getByRole("list", { name: "На что ушло время" }).querySelectorAll("li"),
      (part) => part.textContent?.replace(/\s/g, " "),
    );
    expect(parts).toEqual(["Модели3 150 мс", "Поиск новостей и позиции банка310 мс", "Служебные шаги50 мс"]);
  });

  it("lists the critic verdicts", () => {
    renderTrace("trace-mock-1");

    const verdicts = screen.getByRole("region", { name: "Проверка критика" });
    expect(verdicts.querySelectorAll("li").length).toBe(2);
  });

  it("leads back to the main screen", () => {
    renderTrace("trace-mock-1");

    expect(screen.getByRole("link", { name: "← Главная" }).getAttribute("href")).toBe("/");
  });

  it("opens the details of a step", () => {
    renderTrace("trace-mock-1");
    const plan = screen.getByText("План").closest("details");
    expect(plan?.hasAttribute("open")).toBe(false);

    fireEvent.click(screen.getByText("План"));


    expect(plan?.hasAttribute("open")).toBe(true);
    expect(screen.getByText("Проверить новости логистики, позицию банка и долю отрасли в платежах")).toBeTruthy();
  });

  it.each(["nope", "constructor", "toString"])("says calmly when the trace %s is unknown", (id) => {
    renderTrace(id);

    expect(screen.getByText(/^Трасса не найдена/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "На главную" }).getAttribute("href")).toBe("/");
  });
});
