import { NavLink, Outlet } from "react-router";
import { Brand } from "./Brand";
import { CompanyProvider } from "./company/CompanyContext";
import { useCompany } from "./company/context";
import { COMPANIES } from "./data/companies";
import { EVENTS } from "./data/events";
import { Icon, type IconName } from "./ui/Icon";

const NAV: readonly (readonly [string, string, IconName])[] = [
  ["/", "Главная", "home"],
  ["/events", "События", "events"],
  ["/payments/new", "Платежи", "payment"],
  ["/deposits/new", "Депозиты", "deposit"],
  ["/loans", "Кредиты", "loans"],
  ["/profile", "Профиль", "profile"],
];

const LEGAL_FORM = /^(ООО|АО|ПАО|ЗАО|ИП)\s+/;

function monogram(name: string): string {
  return name.replace(LEGAL_FORM, "").replace(/[«»"]/g, "").trim().charAt(0).toUpperCase();
}

function CompanySwitcher() {
  const { company, select } = useCompany();
  const mark = (
    <span className="company-mark" aria-hidden="true">
      {monogram(company.name)}
    </span>
  );
  if (COMPANIES.length === 1) {
    return (
      <span className="company">
        {mark}
        <span className="company-name">{company.name}</span>
      </span>
    );
  }
  return (
    <span className="company">
      {mark}
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
      <Icon name="chevron-down" size={18} />
    </span>
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

export function Layout() {
  return (
    <CompanyProvider>
      <div className="shell">
        <header className="shell-top">
          <Brand />
          <MainNav />
          <div className="shell-top-end">
            <span className="badge badge-warning">Тестовый режим</span>
            <CompanySwitcher />
          </div>
        </header>
        <main className="shell-main">
          <Outlet />
        </main>
      </div>
    </CompanyProvider>
  );
}
