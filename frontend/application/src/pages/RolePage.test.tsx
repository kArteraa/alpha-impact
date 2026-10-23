import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { loadRole, saveUser } from "../session/storage";
import { TEST_USER } from "../testing";
import { RolePage } from "./RolePage";

function renderRole() {
  render(
    <MemoryRouter initialEntries={["/role"]}>
      <Routes>
        <Route path="/role" element={<RolePage />} />
        <Route path="/login" element={<h1>Вход</h1>} />
        <Route path="/profile" element={<h1>Профиль компании</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("RolePage", () => {
  afterEach(() => {
    cleanup();
    localStorage.clear();
  });

  it("offers every role of the contract", () => {
    saveUser(TEST_USER);
    renderRole();

    const roles = screen.getAllByRole("radio").map((radio) => radio.getAttribute("value"));
    expect(roles).toEqual(["owner", "ceo", "cfo", "treasurer", "chief_accountant"]);
    expect(screen.getByLabelText("Казначей")).toBeTruthy();
  });

  it("keeps the chosen role for the user and opens the profile confirmation", async () => {
    saveUser(TEST_USER);
    renderRole();
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Продолжить" }).disabled).toBe(true);

    fireEvent.click(screen.getByLabelText("Казначей"));
    fireEvent.click(screen.getByRole("button", { name: "Продолжить" }));

    expect(await screen.findByRole("heading", { name: "Профиль компании" })).toBeTruthy();
    expect(loadRole(TEST_USER)).toBe("treasurer");
  });

  it("sends a visitor without a login back to the login screen", async () => {
    renderRole();

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeTruthy();
  });
});
