import { type PageContext, type PanelNotes, useInterpret } from "@alpha-impact/plugin";
import { type FormEvent, useId, useState } from "react";
import { Panel } from "../insight/Panel";
import { PanelPlaceholder } from "../insight/PanelPlaceholder";
import { useInterpretFetcher } from "../insight/useInterpretFetcher";
import { useSession } from "../session/context";

const NEWS_ROWS = 8;

const NEWS_NOTES: PanelNotes = {
  pending: "Размечаю новость и смотрю, что она значит для компании",
  failed: "Не успел разобрать новость",
  silent: "Ничего важного для компании в этой новости",
};

export function NewsPage() {
  const { role } = useSession();
  const urlId = useId();
  const urlHintId = useId();
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [context, setContext] = useState<PageContext | null>(null);
  const insight = useInterpret(context, useInterpretFetcher());
  const news = text.trim();
  const source = url.trim();

  function analyse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (context?.text === news && context.url === source) {
      insight.retry();
      return;
    }
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
          <div className="field field-static">
            <label className="muted" htmlFor={urlId}>
              Ссылка на источник
            </label>
            <input
              id={urlId}
              type="text"
              inputMode="url"
              autoComplete="url"
              value={url}
              placeholder="https://"
              aria-describedby={urlHintId}
              onChange={(event) => setUrl(event.target.value)}
            />
            <small id={urlHintId} className="field-hint">
              Необязательно: если новость по этой ссылке уже есть в ленте, возьму её разметку
            </small>
          </div>
          <div className="form-actions">
            <button className="button" type="submit" disabled={news === "" || insight.pending}>
              Разобрать новость
            </button>
          </div>
        </form>
        <aside>
          {context === null ? (
            <PanelPlaceholder
              title="Разбор новости"
              text="Вставьте новость — Alpha Impact разметит её и покажет, что она значит для компании, со ссылкой на то, как получен вывод"
              steps={[
                ["Текст новости", news !== ""],
                ["Ссылка — по желанию", source !== ""],
              ]}
            />
          ) : (
            <Panel
              actionContext={context}
              role={role}
              response={insight.pending ? undefined : insight.response}
              failed={insight.failed}
              notes={NEWS_NOTES}
              onRetry={insight.retry}
            />
          )}
        </aside>
      </div>
    </section>
  );
}
