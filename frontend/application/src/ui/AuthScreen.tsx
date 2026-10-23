import type { FormEvent, ReactNode } from "react";
import { Brand } from "../Brand";

interface AuthScreenProps {
  title: string;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  children: ReactNode;
}

export function AuthScreen({ title, onSubmit, children }: AuthScreenProps) {
  return (
    <main className="login-screen">
      <form className="login card form" onSubmit={onSubmit}>
        <div className="login-top">
          <Brand />
          <span className="badge badge-warning">Тестовый режим</span>
        </div>
        <h1>{title}</h1>
        {children}
      </form>
    </main>
  );
}
