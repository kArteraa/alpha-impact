import { render } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router";
import { CompanyProvider } from "./company/CompanyContext";

export function renderWithCompany(node: ReactNode, path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CompanyProvider>{node}</CompanyProvider>
    </MemoryRouter>,
  );
}
