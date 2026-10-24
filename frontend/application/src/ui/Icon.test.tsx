import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Icon } from "./Icon";

describe("Icon", () => {
  afterEach(cleanup);

  it("draws a decorative line icon hidden from screen readers", () => {
    const { container } = render(<Icon name="home" />);

    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("aria-hidden")).toBe("true");
    expect(svg?.getAttribute("width")).toBe("20");
    expect(svg?.getAttribute("class")).toBe("icon");
    expect(svg?.querySelector("path")?.getAttribute("d")).toBeTruthy();
  });

  it("takes a size and an extra class", () => {
    const { container } = render(<Icon name="plus" size={24} className="quick-arrow" />);

    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("height")).toBe("24");
    expect(svg?.getAttribute("class")).toBe("icon quick-arrow");
  });
});
