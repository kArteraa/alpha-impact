import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it } from "vitest";
import { AmountField } from "./AmountField";

function Harness({ error = null }: { error?: string | null }) {
  const [value, setValue] = useState("");
  return <AmountField label="Сумма" value={value} onChange={setValue} error={error} />;
}

function input() {
  return screen.getByLabelText<HTMLInputElement>("Сумма, ₽");
}

describe("AmountField", () => {
  afterEach(cleanup);

  it("names the field with its currency", () => {
    render(<Harness />);

    expect(input().getAttribute("inputmode")).toBe("decimal");
    expect(document.querySelector(".amount-suffix")?.textContent).toBe("₽");
  });

  it("formats the amount in rubles when the field loses focus", () => {
    render(<Harness />);
    fireEvent.change(input(), { target: { value: "1500000" } });

    fireEvent.blur(input());

    expect(input().value.replace(/\s/g, " ")).toBe("1 500 000");
  });

  it("explains an error and marks the field invalid", () => {
    render(<Harness error="Сумма — положительное число" />);

    expect(input().getAttribute("aria-invalid")).toBe("true");
    expect(input().getAttribute("aria-describedby")).toBe(screen.getByText("Сумма — положительное число").id);
  });

  it("is valid without an error", () => {
    render(<Harness />);

    expect(input().getAttribute("aria-invalid")).toBe("false");
    expect(input().hasAttribute("aria-describedby")).toBe(false);
  });
});
