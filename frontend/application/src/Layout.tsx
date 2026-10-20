import { NavLink, Outlet } from "react-router";

const NAV = [
  ["/", "Главный"],
  ["/payments/new", "Платёж"],
  ["/deposits/new", "Депозит"],
  ["/loans", "Кредиты"],
  ["/profile", "Профиль"],
] as const;

export function Layout() {
  return (
    <div className="shell">
      <header className="shell-header">
        <span className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Бизнес · Alpha Impact
        </span>
        <nav className="shell-nav">
          {NAV.map(([to, label]) => (
            <NavLink key={to} to={to} end={to === "/"}>
              {label}
            </NavLink>
          ))}
        </nav>
        <span className="badge">Тестовый режим</span>
      </header>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
