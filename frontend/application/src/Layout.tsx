import { NavLink, Outlet } from "react-router";
import { Brand } from "./Brand";
import { CompanyProvider } from "./company/CompanyContext";
import { useCompany } from "./company/context";
import { COMPANIES } from "./data/companies";

const NAV = [
  ["/", "Главная"],
  ["/payments/new", "Платежи"],
  ["/deposits/new", "Депозиты"],
  ["/loans", "Кредиты"],
  ["/profile", "Профиль"],
] as const;

function CompanySwitcher() {
  const { company, select } = useCompany();
  if (COMPANIES.length === 1) {
    return <span className="company-name">{company.name}</span>;
  }
  return (
    <select
      className="company-switcher"
      aria-label="Компания"
      value={company.id}
      onChange={(event) => select(event.target.value)}
    >
      {COMPANIES.map((candidate) => (
        <option key={candidate.id} value={candidate.id}>
          {candidate.name}
        </option>
      ))}
    </select>
  );
}

export function Layout() {
  return (
    <CompanyProvider>
      <div className="shell">
        <header className="shell-top">
          <Brand />
          <CompanySwitcher />
          <span className="badge">Тестовый режим</span>
        </header>
        <nav className="shell-nav" aria-label="Разделы">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <main className="shell-main">
          <Outlet />
        </main>
      </div>
    </CompanyProvider>
  );
}
