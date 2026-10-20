import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ProfilePage } from "./ProfilePage";

function feature(label: string) {
  return screen.getByRole("listitem", { name: label });
}

describe("ProfilePage", () => {
  afterEach(cleanup);

  it("keeps bank facts read-only", () => {
    render(<ProfilePage />);

    const industry = feature("Отрасль");
    expect(within(industry).getByText("по данным банка")).toBeTruthy();
    expect(within(industry).queryByRole("button", { name: "Изменить" })).toBeNull();
  });

  it("edits a derived trait inline", () => {
    render(<ProfilePage />);
    const leasing = feature("Лизинг");
    expect(within(leasing).getByText("определено по данным")).toBeTruthy();

    fireEvent.click(within(leasing).getByRole("button", { name: "Изменить" }));
    fireEvent.change(within(leasing).getByRole("textbox", { name: "Лизинг" }), {
      target: { value: "нет, парк собственный" },
    });
    fireEvent.click(within(leasing).getByRole("button", { name: "Сохранить" }));

    expect(within(leasing).getByText("нет, парк собственный")).toBeTruthy();
    expect(within(leasing).getByText("изменено вами")).toBeTruthy();
    expect(document.querySelector("[role=dialog]")).toBeNull();
  });

  it("drops an edit on cancel", () => {
    render(<ProfilePage />);
    const leasing = feature("Лизинг");

    fireEvent.click(within(leasing).getByRole("button", { name: "Изменить" }));
    fireEvent.change(within(leasing).getByRole("textbox", { name: "Лизинг" }), { target: { value: "нет" } });
    fireEvent.click(within(leasing).getByRole("button", { name: "Отмена" }));

    expect(within(leasing).getByText("да")).toBeTruthy();
  });
});
