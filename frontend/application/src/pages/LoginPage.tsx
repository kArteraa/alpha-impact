import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";
import { Brand } from "../Brand";
import { loadRole, saveUser } from "../session/storage";
import { Icon } from "../ui/Icon";

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
    <main className="login-screen">
      <form className="login card form" onSubmit={submit}>
        <div className="login-top">
          <Brand />
          <span className="badge badge-warning">Тестовый режим</span>
        </div>
        <h1>Вход</h1>
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
        {error && (
          <p className="error" role="alert">
            <Icon name="alert" size={18} />
            {error}
          </p>
        )}
      </form>
    </main>
  );
}
