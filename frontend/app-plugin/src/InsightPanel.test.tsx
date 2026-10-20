import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { InsightPanel } from "./InsightPanel";
import { mockResponses } from "./mocks";

const context = { type: "payment", amount: 1500000 } as const;

describe("InsightPanel", () => {
  afterEach(cleanup);

  it("shows the checking state while there is no response", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.checking} />);
    expect(screen.getByText(/Проверяю/)).toBeTruthy();
    expect(document.querySelector('[data-state="checking"]')).not.toBeNull();
  });

  it("shows explicit silence in one line", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.silent} />);
    expect(screen.getByText("По этому действию ничего важного.")).toBeTruthy();
    expect(document.querySelector('[data-state="silent"]')).not.toBeNull();
  });

  it("renders a card with all three claim types and their sources", () => {
    const { container } = render(
      <InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />,
    );
    expect(screen.getByRole("heading", { level: 2 })).toBeTruthy();
    for (const label of ["факт", "позиция банка", "вывод AI"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(container.querySelectorAll("[data-claim-type]").length).toBe(5);
    expect(screen.getByText("Аккредитив")).toBeTruthy();
    expect(screen.getByText("Как получен вывод").getAttribute("href")).toBe("/trace/trace-mock-1");
  });
});
