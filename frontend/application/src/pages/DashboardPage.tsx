import { Link } from "react-router";

const QUICK_ACTIONS = [
  ["/payments/new", "Платёж", "Контрагенту по реквизитам"],
  ["/deposits/new", "Депозит", "Разместить свободные средства"],
  ["/loans", "Кредиты", "Портфель и новый транш"],
] as const;

export function DashboardPage() {
  return (
    <section>
      <h1>Главный экран</h1>
      <div className="dashboard-grid">
        <div className="card account">
          <span className="muted">Расчётный счёт ·· 4417</span>
          <strong className="balance">48 250 300,00 ₽</strong>
          <span className="muted">Доступно сегодня</span>
        </div>
        <nav className="quick-actions" aria-label="Быстрые действия">
          {QUICK_ACTIONS.map(([to, title, caption]) => (
            <Link key={to} to={to} className="card quick-action">
              <strong>{title}</strong>
              <span className="muted">{caption}</span>
            </Link>
          ))}
        </nav>
        <div className="card widget-slot" data-slot="dashboard-widget">
          <h2>Что изменилось вокруг ваших операций</h2>
          <p className="muted">Персональная лента событий появится в задаче AH-32.</p>
        </div>
      </div>
    </section>
  );
}
