import type { Role } from "@alpha-impact/plugin";
import { createContext, useContext } from "react";
import type { Company } from "../data/companies";

export interface CompanyValue {
  company: Company;
  companies: Company[];
  select: (companyId: string) => void;
  userId: string;
  role: Role;
}

export const CompanyContext = createContext<CompanyValue | null>(null);

export function useCompany(): CompanyValue {
  const value = useContext(CompanyContext);
  if (value === null) {
    throw new Error("useCompany must be used inside CompanyProvider");
  }
  return value;
}
