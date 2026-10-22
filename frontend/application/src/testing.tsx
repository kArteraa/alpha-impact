import type { Role } from "@alpha-impact/plugin";
import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter, Route, Routes } from "react-router";
import { vi } from "vitest";
import { App } from "./App";
import { CompanyContext } from "./company/context";
import { companyOf } from "./data/companies";
import { saveRole, saveUser } from "./session/storage";

export const TEST_USER = "user_cfo_wholesale";
export const TEST_CLIENT = "U_1941";

type Reply = readonly [status: number, body: unknown];

export function stubApi(routes: Record<string, Reply>) {
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const reply = routes[key];
    if (reply === undefined) {
      return Promise.reject(new Error(`No stub for ${key}`));
    }
    return Promise.resolve(new Response(JSON.stringify(reply[1]), { status: reply[0] }));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function signIn(userId = TEST_USER, role: Role = "cfo") {
  saveUser(userId);
  saveRole(userId, role);
}

export function renderWithCompany(node: ReactNode, path = "/", role: Role = "cfo") {
  const company = companyOf(TEST_CLIENT);
  const value = { company, companies: [company], select: () => {}, userId: TEST_USER, role };
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CompanyContext.Provider value={value}>
        <Routes>
          <Route path={path} element={node} />
          <Route path="/" element={<h1>Главный экран</h1>} />
        </Routes>
      </CompanyContext.Provider>
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
