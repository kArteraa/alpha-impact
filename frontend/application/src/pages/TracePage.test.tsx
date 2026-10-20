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

  it("opens the details of a step", () => {
    renderTrace("trace-mock-1");
    const plan = screen.getByText("План").closest("details");
    expect(plan?.hasAttribute("open")).toBe(false);

    fireEvent.click(screen.getByText("План"));

    expect(plan?.hasAttribute("open")).toBe(true);
    expect(screen.getByText("Проверить новости логистики, позицию банка и долю отрасли в платежах")).toBeTruthy();
  });

  it("says calmly when the trace is unknown", () => {
    renderTrace("nope");

    expect(screen.getByText(/^Трасса не найдена/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "На главную" }).getAttribute("href")).toBe("/");
  });
});
