import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { loadRole, saveUser } from "../session/storage";
import { Alert } from "../ui/Alert";
import { AuthScreen } from "../ui/AuthScreen";

export function LoginPage() {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      const session = await api.authMock(userId.trim());
      saveUser(session.user_id);
      navigate(loadRole(session.user_id) === null ? "/role" : "/profile");
    } catch (failure) {
      setError(failure instanceof ApiError ? `Вход не удался (${failure.status})` : "Сервер недоступен");
    }
  }

  return (
    <AuthScreen title="Вход" onSubmit={submit}>
      <label className="field">
        <span className="muted">Тестовый пользователь</span>
        <input
          name="user_id"
          value={userId}
          placeholder="user_cfo_wholesale"
          onChange={(event) => setUserId(event.target.value)}
          required
        />
      </label>
      <button className="button button-block" type="submit" disabled={userId.trim() === ""}>
        Войти
      </button>
      {error && <Alert text={error} />}
    </AuthScreen>
  );
}
