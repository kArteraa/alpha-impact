import { type FormEvent, useState } from "react";
import type { ExtensionState, Send } from "../messages";

interface LoginProps {
  send: Send;
  onState: (state: ExtensionState) => void;
}

export function Login({ send, onState }: LoginProps) {
  const [userId, setUserId] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSending(true);
    const reply = await send({ type: "login", userId: userId.trim() });
    setSending(false);
    if (reply.ok) {
      onState(reply.value);
    } else {
      setError(reply.error === "http" ? `Вход не удался (${reply.status})` : "Сервер недоступен");
    }
  }

  return (
    <form className="popup-form" onSubmit={submit}>
      <label className="popup-field">
        <span>Тестовый пользователь</span>
        <input value={userId} placeholder="user_cfo_wholesale" onChange={(event) => setUserId(event.target.value)} />
      </label>
      <button className="popup-button" type="submit" disabled={sending || userId.trim() === ""}>
        Войти
      </button>
      {error && (
        <p className="popup-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}
