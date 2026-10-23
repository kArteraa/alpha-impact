import { NavLink, Outlet } from "react-router";
import { Brand } from "./Brand";
import { CompanyProvider } from "./company/CompanyContext";
import { useCompany } from "./company/context";
import { EVENTS } from "./data/events";
import { Icon, type IconName } from "./ui/Icon";
import { stripLegalForm } from "./ui/listbox";
import { Mark, Select } from "./ui/Select";

const NAV: readonly (readonly [string, string, IconName])[] = [
  ["/", "Главная", "home"],
  ["/events", "События", "events"],
  ["/payments/new", "Платежи", "payment"],
  ["/deposits/new", "Депозиты", "deposit"],
  ["/loans", "Кредиты", "loans"],
  ["/profile", "Профиль", "profile"],
];

function monogram(name: string): string {
  return stripLegalForm(name).charAt(0).toUpperCase();
}

function CompanySwitcher() {
  const { company, companies, select } = useCompany();
  if (companies.length === 1) {
    return (
      <span className="company">
        <Mark text={monogram(company.name)} />
        <span className="company-name">{company.name}</span>
      </span>
    );
  }
  return (
    <Select
      label="Компания"
      variant="pill"
      value={company.id}
      options={companies.map((candidate) => ({
        value: candidate.id,
        label: candidate.name,
        hint: candidate.account ? `Счёт ${candidate.account}` : undefined,
        mark: monogram(candidate.name),
      }))}
      onChange={select}
    />
  );
}

function MainNav() {
  const { company } = useCompany();
  const eventCount = EVENTS[company.id]?.length ?? 0;
  return (
    <nav className="main-nav" aria-label="Разделы">
      {NAV.map(([to, label, icon]) => (
        <NavLink key={to} to={to} end={to === "/"} title={label}>
          {({ isActive }) => (
            <>
              <span className="nav-icon">
                <Icon name={icon} />
                {to === "/events" && eventCount > 0 && (
                  <span className="nav-count" aria-hidden="true">
                    {eventCount}
                  </span>
                )}
              </span>
              <span className={isActive ? "nav-label" : "visually-hidden"}>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function Shell() {
  const { company } = useCompany();
  return (
    <div className="shell">
      <header className="shell-top">
        <Brand />
        <MainNav />
        <div className="shell-top-end">
          <span className="badge badge-warning">Тестовый режим</span>
          <CompanySwitcher />
        </div>
      </header>
      <main className="shell-main" key={company.id}>
        <Outlet />
      </main>
    </div>
  );
}

export function Layout() {
  return (
    <CompanyProvider>
      <Shell />
    </CompanyProvider>
  );
}
