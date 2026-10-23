import type { Role } from "@alpha-impact/plugin";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";
import { App } from "./App";
import { CompanyContext } from "./company/context";
import { companyOf } from "./data/companies";
import { SessionContext } from "./session/context";
import { saveRole, saveUser } from "./session/storage";

export const TEST_USER = "user_cfo_wholesale";
export const TEST_CLIENT = "U_1941";

type Reply = readonly [status: number, body: unknown];

export function stubApi(routes: Record<string, Reply | ((init?: RequestInit) => Reply)>) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const route = routes[key];
    if (route === undefined) {
      return Promise.reject(new Error(`No stub for ${key}`));
    }
    const [status, body] = typeof route === "function" ? route(init) : route;
    return Promise.resolve(new Response(JSON.stringify(body), { status }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function chooseOption(label: string, option: string | RegExp) {
  fireEvent.click(screen.getByRole("combobox", { name: label }));
  fireEvent.click(screen.getByRole("option", { name: option }));
}

export function signIn(userId = TEST_USER, role: Role = "cfo") {
  saveUser(userId);
  saveRole(userId, role);
}

interface PageOptions {
  path?: string;
  role?: Role;
  routes?: ReactNode;
}

export function renderWithCompany(node: ReactNode, { path = "/", role = "cfo", routes }: PageOptions = {}) {
  const company = companyOf(TEST_CLIENT);
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SessionContext.Provider value={{ userId: TEST_USER, role }}>
        <CompanyContext.Provider value={{ company, companies: [company], select: () => {} }}>
          <Routes>
            <Route path={path} element={node} />
            {routes}
          </Routes>
        </CompanyContext.Provider>
      </SessionContext.Provider>
    </MemoryRouter>,
  );
}

export function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
