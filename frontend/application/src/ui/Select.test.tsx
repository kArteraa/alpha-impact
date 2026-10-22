import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Select, type SelectOption } from "./Select";

const OPTIONS: SelectOption[] = [
  { value: "U_96105", label: "ООО «Северо-Западная логистика»", hint: "Грузоперевозки, Санкт-Петербург" },
  { value: "U_22524", label: "ООО «Канцмир»", hint: "Канцелярские товары, Москва" },
  { value: "U_3", label: "АО «СтройЛизинг»" },
];

function Harness({ onChange }: { onChange: (value: string) => void }) {
  const [value, setValue] = useState("");
  return (
    <>
      <Select
        label="Получатель"
        value={value}
        options={OPTIONS}
        placeholder="Выберите контрагента"
        onChange={(next) => {
          setValue(next);
          onChange(next);
        }}
      />
      <button type="button">Снаружи</button>
    </>
  );
}

function setup() {
  const onChange = vi.fn();
  render(<Harness onChange={onChange} />);
  return { onChange, combobox: screen.getByRole("combobox", { name: "Получатель" }) };
}

function key(target: Element, name: string) {
  fireEvent.keyDown(target, { key: name });
}

describe("Select", () => {
  afterEach(cleanup);

  it("shows the placeholder in a closed combobox named by its label", () => {
    const { combobox } = setup();

    expect(combobox.textContent).toContain("Выберите контрагента");
    expect(combobox.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("opens on click and lists the options with their hints", () => {
    const { combobox } = setup();

    fireEvent.click(combobox);

    expect(combobox.getAttribute("aria-expanded")).toBe("true");
    const options = screen.getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "ООО «Северо-Западная логистика»Грузоперевозки, Санкт-Петербург",
      "ООО «Канцмир»Канцелярские товары, Москва",
      "АО «СтройЛизинг»",
    ]);
    expect(combobox.getAttribute("aria-controls")).toBe(screen.getByRole("listbox").id);
  });

  it("chooses an option with a click and closes", () => {
    const { combobox, onChange } = setup();
    fireEvent.click(combobox);

    fireEvent.click(screen.getByRole("option", { name: /Канцмир/ }));

    expect(onChange).toHaveBeenCalledWith("U_22524");
    expect(combobox.textContent).toContain("ООО «Канцмир»");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("marks the chosen option as selected", () => {
    const { combobox } = setup();
    fireEvent.click(combobox);
    fireEvent.click(screen.getByRole("option", { name: /Канцмир/ }));

    fireEvent.click(combobox);

    expect(screen.getByRole("option", { name: /Канцмир/ }).getAttribute("aria-selected")).toBe("true");
    expect(screen.getByRole("option", { name: /логистика/ }).getAttribute("aria-selected")).toBe("false");
  });

  it("moves through the options and chooses with the keyboard", () => {
    const { combobox, onChange } = setup();

    key(combobox, "ArrowDown");
    expect(combobox.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[0].id);
    key(combobox, "ArrowDown");
    expect(combobox.getAttribute("aria-activedescendant")).toBe(screen.getAllByRole("option")[1].id);
    key(combobox, "Enter");

    expect(onChange).toHaveBeenCalledWith("U_22524");
    expect(combobox.getAttribute("aria-expanded")).toBe("false");
  });

  it("jumps to the last option with End", () => {
    const { combobox, onChange } = setup();

    key(combobox, "End");
    key(combobox, " ");

    expect(onChange).toHaveBeenCalledWith("U_3");
  });

  it("closes on Escape without changing the value", () => {
    const { combobox, onChange } = setup();
    key(combobox, "ArrowDown");

    key(combobox, "Escape");

    expect(screen.queryByRole("listbox")).toBeNull();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("finds an option by the first letters of the company name", () => {
    const { combobox } = setup();

    key(combobox, "к");

    expect(combobox.getAttribute("aria-activedescendant")).toBe(screen.getByRole("option", { name: /Канцмир/ }).id);
  });

  it("closes on a click outside", () => {
    const { combobox, onChange } = setup();
    fireEvent.click(combobox);

    fireEvent.mouseDown(screen.getByRole("button", { name: "Снаружи" }));

    expect(screen.queryByRole("listbox")).toBeNull();
    expect(onChange).not.toHaveBeenCalled();
  });
});
