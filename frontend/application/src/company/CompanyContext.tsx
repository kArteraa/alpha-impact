import { type ReactNode, useState } from "react";
import { Navigate } from "react-router";
import { ApiError, api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { companyOf } from "../data/companies";
import { Alert } from "../ui/Alert";
import { CompanyContext } from "./context";

function Failure({ text }: { text: string }) {
  return (
    <main className="shell-main">
      <Alert text={text} />
    </main>
  );
}

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [clients] = useLoad(api.clients);
  const [companyId, setCompanyId] = useState<string | null>(null);

  if (clients.status === "loading") {
    return null;
  }
  if (clients.status === "failed") {
    if (clients.error instanceof ApiError && clients.error.status === 401) {
      return <Navigate to="/login" replace />;
    }
    return <Failure text="Не удалось загрузить компании" />;
  }
  if (clients.value.length === 0) {
    return <Failure text="Нет компаний, доступных этому пользователю" />;
  }
  const companies = clients.value.map(companyOf);
  const company = companies.find((candidate) => candidate.id === companyId) ?? companies[0];
  return (
    <CompanyContext.Provider value={{ company, companies, select: setCompanyId }}>{children}</CompanyContext.Provider>
  );
}
