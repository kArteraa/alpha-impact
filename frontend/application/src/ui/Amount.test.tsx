import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RUB } from "../money";
import { Amount } from "./Amount";

describe("Amount", () => {
  afterEach(cleanup);

  it("reads exactly as the ruble format and mutes the kopecks", () => {
    const { container } = render(<Amount value={48_250_300} className="account-amount" testId="balance" />);

    const amount = container.querySelector("strong");
    expect(amount?.textContent).toBe(RUB.format(48_250_300));
    expect(amount?.querySelector(".amount-tail")?.textContent).toBe(RUB.format(48_250_300).slice(-5));
    expect(amount?.className).toBe("account-amount");
    expect(amount?.dataset.testid).toBe("balance");
  });
});
