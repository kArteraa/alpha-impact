import { type ReactNode, useEffect, useState } from "react";
import { Navigate } from "react-router";
import { ApiError, api } from "../api/client";
import { type Company, companyOf } from "../data/companies";
import { loadRole, loadUser } from "../session/storage";
import { Icon } from "../ui/Icon";
import { CompanyContext } from "./context";

type Clients =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "failed"; message: string }
  | { status: "ready"; companies: Company[] };

function failureOf(failure: unknown): Clients {
  if (failure instanceof ApiError && failure.status === 401) {
    return { status: "signed-out" };
  }
  return { status: "failed", message: "Не удалось загрузить компании" };
}

function clientsOf(ids: string[]): Clients {
  if (ids.length === 0) {
    return { status: "failed", message: "Нет компаний, доступных этому пользователю" };
  }
  return { status: "ready", companies: ids.map(companyOf) };
}

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [userId] = useState(loadUser);
  const [role] = useState(() => (userId === null ? null : loadRole(userId)));
  const [clients, setClients] = useState<Clients>({ status: "loading" });
  const [companyId, setCompanyId] = useState<string | null>(null);

  useEffect(() => {
    if (userId === null || role === null) {
      return;
    }
    let active = true;
    api.clients().then(
      (ids) => {
        if (active) {
          setClients(clientsOf(ids));
        }
      },
      (failure: unknown) => {
        if (active) {
          setClients(failureOf(failure));
        }
      },
    );
    return () => {
      active = false;
    };
  }, [userId, role]);

  if (userId === null || clients.status === "signed-out") {
    return <Navigate to="/login" replace />;
  }
  if (role === null) {
    return <Navigate to="/role" replace />;
  }
  if (clients.status === "loading") {
    return null;
  }
  if (clients.status === "failed") {
    return (
      <main className="shell-main">
        <p className="error" role="alert">
          <Icon name="alert" size={18} />
          {clients.message}
        </p>
      </main>
    );
  }
  const company = clients.companies.find((candidate) => candidate.id === companyId) ?? clients.companies[0];
  return (
    <CompanyContext.Provider value={{ company, companies: clients.companies, select: setCompanyId, userId, role }}>
      {children}
    </CompanyContext.Provider>
  );
}
