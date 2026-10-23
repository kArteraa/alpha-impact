import { type FormEvent, useState } from "react";
import type { ExtensionState, Send, WorkerReply } from "../messages";

interface LoginProps {
  send: Send;
  onState: (state: ExtensionState) => void;
}

function failureText(reply: Extract<WorkerReply<unknown>, { ok: false }>): string {
  return reply.error === "http" ? `Вход не удался (${reply.status})` : "Сервер недоступен";
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
      setError(failureText(reply));
    }
  }

  return (
    <form className="popup-form" onSubmit={submit}>
      <label className="popup-field">
        <span>Тестовый пользователь</span>
        <input
          name="user_id"
          value={userId}
          placeholder="user_cfo_wholesale"
          onChange={(event) => setUserId(event.target.value)}
          required
        />
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
