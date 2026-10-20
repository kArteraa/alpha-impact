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
    <form className="login card" onSubmit={submit}>
      <h1>Вход</h1>
      <label>
        Тестовый пользователь
        <input
          name="user_id"
          value={userId}
          placeholder="user_cfo_wholesale"
          onChange={(event) => setUserId(event.target.value)}
          required
        />
      </label>
      <button type="submit">Войти</button>
      {error && <p role="alert">{error}</p>}
    </form>
  );
}
