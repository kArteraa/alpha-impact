import type { Role } from "@alpha-impact/plugin";
import { type FormEvent, useId, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { ROLE_LABELS } from "../session/roles";
import { loadUser, saveRole } from "../session/storage";
import { AuthScreen } from "../ui/AuthScreen";

const ROLES = Object.entries(ROLE_LABELS) as [Role, string][];

export function RolePage() {
  const hintId = useId();
  const [role, setRole] = useState<Role | null>(null);
  const navigate = useNavigate();
  const userId = loadUser();

  if (userId === null) {
    return <Navigate to="/login" replace />;
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (role !== null) {
      saveRole(userId, role);
      navigate("/profile");
    }
  };

  return (
    <AuthScreen title="Ваша роль" onSubmit={submit}>
      <span id={hintId} className="muted">
        Alpha Impact расставит акценты под ваши задачи
      </span>
      <div className="segmented segmented-stack" role="radiogroup" aria-labelledby={hintId}>
        {ROLES.map(([value, label]) => (
          <label key={value}>
            <input type="radio" name="role" value={value} checked={role === value} onChange={() => setRole(value)} />
            <span>{label}</span>
          </label>
        ))}
      </div>
      <button className="button button-block" type="submit" disabled={role === null}>
        Продолжить
      </button>
    </AuthScreen>
  );
}
