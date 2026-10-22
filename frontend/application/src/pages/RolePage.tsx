import type { Role } from "@alpha-impact/plugin";
import { type FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { Brand } from "../Brand";
import { ROLE_LABELS } from "../session/roles";
import { loadUser, saveRole } from "../session/storage";

const ROLES = Object.entries(ROLE_LABELS) as [Role, string][];

export function RolePage() {
  const [userId] = useState(loadUser);
  const [role, setRole] = useState<Role | null>(null);
  const navigate = useNavigate();

  if (userId === null) {
    return <Navigate to="/login" replace />;
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (userId !== null && role !== null) {
      saveRole(userId, role);
      navigate("/profile");
    }
  }

  return (
    <main className="login-screen">
      <form className="login card form" onSubmit={submit}>
        <div className="login-top">
          <Brand />
          <span className="badge badge-warning">Тестовый режим</span>
        </div>
        <h1>Ваша роль</h1>
        <fieldset className="role-options">
          <legend className="muted">Alpha Impact расставит акценты под ваши задачи</legend>
          {ROLES.map(([value, label]) => (
            <label key={value} className="role-option">
              <input type="radio" name="role" value={value} checked={role === value} onChange={() => setRole(value)} />
              {label}
            </label>
          ))}
        </fieldset>
        <button className="button button-block" type="submit" disabled={role === null}>
          Продолжить
        </button>
      </form>
    </main>
  );
}
