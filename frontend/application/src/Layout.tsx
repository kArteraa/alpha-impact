import { NavLink, Outlet } from "react-router";
import { Brand } from "./Brand";

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
        <Brand />
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
