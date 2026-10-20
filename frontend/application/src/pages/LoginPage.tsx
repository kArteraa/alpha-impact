import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, api } from "../api/client";

export function LoginPage() {
  const [userId, setUserId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      await api.authMock(userId);
      navigate("/");
    } catch (failure) {
      setError(failure instanceof ApiError ? `Вход не удался (${failure.status})` : "Сервер недоступен");
    }
  }

  return (
    <main className="login-screen">
      <form className="login card form" onSubmit={submit}>
        <span className="brand">
          <span className="brand-mark" aria-hidden="true" />
          Бизнес · Alpha Impact
        </span>
        <h1>Вход</h1>
        <label className="field">
          <span>Тестовый пользователь</span>
          <input
            name="user_id"
            value={userId}
            placeholder="user_cfo_wholesale"
            onChange={(event) => setUserId(event.target.value)}
            required
          />
        </label>
        <button className="button button-primary" type="submit">
          Войти
        </button>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
      </form>
    </main>
  );
}
