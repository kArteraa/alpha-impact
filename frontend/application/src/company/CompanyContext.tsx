import { type ReactNode, useState } from "react";
import { COMPANIES } from "../data/companies";
import { CompanyContext } from "./context";

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companyId, setCompanyId] = useState(COMPANIES[0].id);
  const company = COMPANIES.find((candidate) => candidate.id === companyId) ?? COMPANIES[0];
  return (
    <CompanyContext.Provider value={{ company, select: setCompanyId }}>
      {children}
    </CompanyContext.Provider>
  );
}
