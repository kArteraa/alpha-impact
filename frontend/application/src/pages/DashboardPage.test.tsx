import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { DashboardPage } from "./DashboardPage";

describe("DashboardPage", () => {
  afterEach(cleanup);

  it("reserves a slot for the feed widget", () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(document.querySelector('[data-slot="dashboard-widget"]')).not.toBeNull();
  });

  it.each([
    ["Платёж", "/payments/new"],
    ["Депозит", "/deposits/new"],
    ["Кредиты", "/loans"],
  ])("links the %s quick action to %s", (name, href) => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: new RegExp(`^${name}`) }).getAttribute("href")).toBe(href);
  });
});
