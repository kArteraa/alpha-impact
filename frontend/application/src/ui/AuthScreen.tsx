import { ClaimTypeBadge, type ClaimType } from "@alpha-impact/plugin";
import type { FormEvent, ReactNode } from "react";
import { Brand } from "../Brand";

interface AuthScreenProps {
  title: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}

const LEGEND: readonly (readonly [ClaimType, string])[] = [
  ["fact", "новость или данные вашей компании"],
  ["bank", "позиция аналитиков Альфа-Банка из отчёта"],
  ["ai", "вывод модели, всегда со ссылкой на основание"],
];

export function AuthScreen({ title, onSubmit, children }: AuthScreenProps) {
  return (
    <main className="login-screen">
      <div className="auth">
        <aside className="auth-intro">
          <Brand />
          <p className="auth-lead">События, которые важны вашему бизнесу, — с объяснением и источником</p>
          <ul className="auth-legend">
            {LEGEND.map(([type, text]) => (
              <li key={type}>
                <ClaimTypeBadge type={type} />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </aside>
        <form className="login card form" onSubmit={onSubmit}>
          <div className="login-top">
            <span className="login-brand">
              <Brand />
            </span>
            <span className="badge badge-warning">Тестовый режим</span>
          </div>
          <h1>{title}</h1>
          {children}
        </form>
      </div>
    </main>
  );
}
