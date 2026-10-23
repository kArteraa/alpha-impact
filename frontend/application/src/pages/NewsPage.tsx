import type { PageContext, PanelNotes } from "@alpha-impact/plugin";
import { type FormEvent, useState } from "react";
import { ActionPanel } from "../insight/ActionPanel";
import { PanelPlaceholder } from "../insight/PanelPlaceholder";

const NEWS_ROWS = 8;

const NEWS_NOTES: PanelNotes = {
  pending: "Размечаю новость и смотрю, что она значит для компании",
  failed: "Не успел разобрать новость — модель не ответила вовремя или недоступна",
  silent: "Ничего важного для компании в этой новости",
};

export function NewsPage() {
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [context, setContext] = useState<PageContext | null>(null);
  const news = text.trim();
  const source = url.trim();

  function analyse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setContext({ type: "page", url: source, text: news });
  }

  return (
    <section>
      <h1>Живая новость</h1>
      <div className="page-grid">
        <form className="card form" onSubmit={analyse}>
          <h2>Вставить новость</h2>
          <label className="field field-static">
            <span className="muted">Текст новости</span>
            <textarea
              rows={NEWS_ROWS}
              value={text}
              placeholder="Заголовок первой строкой, ниже — текст"
              onChange={(event) => setText(event.target.value)}
            />
          </label>
          <label className="field field-static">
            <span className="muted">Ссылка на источник</span>
            <input type="url" value={url} placeholder="https://" onChange={(event) => setUrl(event.target.value)} />
          </label>
          <div className="form-actions">
            <button className="button" type="submit" disabled={news === ""}>
              Разобрать новость
            </button>
          </div>
        </form>
        <aside>
          <ActionPanel
            context={context}
            notes={NEWS_NOTES}
            placeholder={
              <PanelPlaceholder
                title="Разбор новости"
                text="Вставьте новость — Alpha Impact разметит её и покажет, что она значит для компании, со ссылкой на то, как получен вывод"
                steps={[
                  ["Текст новости", news !== ""],
                  ["Ссылка — по желанию", source !== ""],
                ]}
              />
            }
          />
        </aside>
      </div>
    </section>
  );
}
