import { createContext, type ReactNode, useContext, useState } from "react";
import { COMPANIES, type Company } from "../data/companies";

interface CompanyValue {
  company: Company;
  companies: Company[];
  select: (companyId: string) => void;
}

const CompanyContext = createContext<CompanyValue | null>(null);

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [companyId, setCompanyId] = useState(COMPANIES[0].id);
  const company = COMPANIES.find((candidate) => candidate.id === companyId) ?? COMPANIES[0];
  return (
    <CompanyContext.Provider value={{ company, companies: COMPANIES, select: setCompanyId }}>
      {children}
    </CompanyContext.Provider>
  );
}

export function useCompany(): CompanyValue {
  const value = useContext(CompanyContext);
  if (value === null) {
    throw new Error("useCompany must be used inside CompanyProvider");
  }
  return value;
}
