import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Showcase } from "./Showcase";

describe("Showcase", () => {
  afterEach(cleanup);

  it("shows every panel state", () => {
    render(<Showcase />);

    const states = Array.from(document.querySelectorAll(".insight-panel"), (panel) => panel.getAttribute("data-state"));
    expect(new Set(states)).toEqual(new Set(["checking", "silent", "failed", "cards"]));
    expect(screen.getAllByRole("progressbar").length).toBe(1);
  });

  it("shows the three claim badges", () => {
    render(<Showcase />);

    const badges = screen.getByRole("region", { name: "Пометки тезисов" });
    expect(Array.from(badges.querySelectorAll(".claim-badge"), (badge) => badge.textContent)).toEqual([
      "■Факт",
      "◆Банк",
      "✦AI",
    ]);
  });

  it("shows the panel in both container widths", () => {
    render(<Showcase />);

    expect(document.querySelector('[data-width="400"] .insight-panel')).not.toBeNull();
    expect(document.querySelector('[data-width="320"] .insight-panel-compact')).not.toBeNull();
  });
});
