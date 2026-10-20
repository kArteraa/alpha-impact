import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { DashboardPage } from "./DashboardPage";

function renderDashboard() {
  render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  afterEach(cleanup);

  it("reserves a slot for the feed widget", () => {
    renderDashboard();

    expect(document.querySelector('[data-slot="dashboard-widget"]')).not.toBeNull();
  });

  it.each([
    ["Платёж", "/payments/new"],
    ["Депозит", "/deposits/new"],
    ["Кредиты", "/loans"],
  ])("links the %s quick action to %s", (name, href) => {
    renderDashboard();

    expect(screen.getByRole("link", { name: new RegExp(`^${name}`) }).getAttribute("href")).toBe(href);
  });
});
