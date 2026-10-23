import { ROLES, type Role } from "@alpha-impact/plugin";
import { type FormEvent, useId, useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { ROLE_FOCUS } from "../session/roles";
import { loadUser, saveRole } from "../session/storage";
import { AuthScreen } from "../ui/AuthScreen";
import { Icon } from "../ui/Icon";

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
      <div className="choice-list" role="radiogroup" aria-labelledby={hintId}>
        {ROLES.map(([value, label]) => (
          <label key={value} className="choice">
            <input
              type="radio"
              name="role"
              value={value}
              checked={role === value}
              aria-labelledby={`${hintId}-${value}`}
              aria-describedby={`${hintId}-${value}-focus`}
              onChange={() => setRole(value)}
            />
            <span className="choice-body">
              <span id={`${hintId}-${value}`} className="choice-title">
                {label}
              </span>
              <span id={`${hintId}-${value}-focus`} className="choice-hint">
                {ROLE_FOCUS[value]}
              </span>
              <span className="choice-mark" aria-hidden="true">
                <Icon name="check" size={14} />
              </span>
            </span>
          </label>
        ))}
      </div>
      <button className="button button-block" type="submit" disabled={role === null}>
        Продолжить
      </button>
    </AuthScreen>
  );
}
