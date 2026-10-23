import { type ReactNode, useMemo, useState } from "react";
import { Link } from "react-router";
import { api } from "../api/client";
import { useLoad } from "../api/useLoad";
import { Brand } from "../Brand";
import { companyOf } from "../data/companies";
import { Alert } from "../ui/Alert";
import { CompanyContext } from "./context";

function Frame({ children }: { children?: ReactNode }) {
  return (
    <div className="shell">
      <header className="shell-top">
        <Brand />
      </header>
      <main className="shell-main">{children}</main>
    </div>
  );
}

function Failure({ text }: { text: string }) {
  return (
    <Frame>
      <Alert text={text} />
      <Link className="button" to="/login">
        Войти заново
      </Link>
    </Frame>
  );
}

export function CompanyProvider({ children }: { children: ReactNode }) {
  const [clients] = useLoad(api.clients);
  const [companyId, setCompanyId] = useState<string | null>(null);
  const companies = useMemo(() => (clients.status === "ready" ? clients.value.map(companyOf) : []), [clients]);
  const value = useMemo(() => {
    const company = companies.find((candidate) => candidate.id === companyId) ?? companies[0];
    return company && { company, companies, select: setCompanyId };
  }, [companies, companyId]);

  if (clients.status === "loading") {
    return <Frame />;
  }
  if (clients.status === "failed") {
    return <Failure text="Не удалось загрузить компании" />;
  }
  if (value === undefined) {
    return <Failure text="Нет компаний, доступных этому пользователю" />;
  }
  return <CompanyContext.Provider value={value}>{children}</CompanyContext.Provider>;
}
