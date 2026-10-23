import { useEffect, useState } from "react";
import { InsightPanel, type InterpretFetcher, type InterpretResponse, type PageContext, type Role, useInterpret } from "../../src";
import { API_BASE } from "../config";
import type { DetectedPage, ExtensionState, Send } from "../messages";

export interface PanelHost {
  activePage(): Promise<DetectedPage | null>;
  subscribe(listener: () => void): () => void;
}

interface View {
  state: ExtensionState;
  detected: DetectedPage | null;
}

const UNRECOGNISED_PAGE: PageContext = { type: "page", url: "", text: "" };
const UNRECOGNISED_RESPONSE: InterpretResponse = {
  silent: true,
  silent_reason: "Страница не похожа на статью, карточку контрагента, тендер или курс валют",
  cards: [],
  cached: false,
};

function PageInsight({ page, role, send }: { page: PageContext; role: Role; send: Send }) {
  const context: PageContext = { ...page, type: "page" };
  const fetcher: InterpretFetcher = async () => {
    const reply = await send({ type: "interpret", page });
    if (!reply.ok) {
      throw new Error(reply.error);
    }
    return reply.value;
  };
  const insight = useInterpret(context, fetcher);
  return (
    <InsightPanel
      actionContext={context}
      role={role}
      response={insight.response}
      pending={insight.pending}
      failed={insight.failed}
      onRetry={insight.retry}
      compact
      apiBase={API_BASE}
    />
  );
}

function Content({ view, send }: { view: View; send: Send }) {
  const { state, detected } = view;
  if (!state.signedIn) {
    return <p className="sidepanel-note">Войдите в расширение: нажмите на значок Alpha Impact</p>;
  }
  const { clientId, role } = state.settings;
  if (clientId === null || role === null) {
    return <p className="sidepanel-note">Выберите компанию и роль в окне расширения</p>;
  }
  if (detected === null) {
    return <InsightPanel actionContext={UNRECOGNISED_PAGE} role={role} response={UNRECOGNISED_RESPONSE} compact />;
  }
  return <PageInsight key={JSON.stringify([clientId, role, detected.page.url])} page={detected.page} role={role} send={send} />;
}

export function SidePanel({ send, host }: { send: Send; host: PanelHost }) {
  const [view, setView] = useState<View | null>(null);

  useEffect(() => {
    let latest = 0;
    function refresh() {
      const run = ++latest;
      void Promise.all([send({ type: "state" }), host.activePage()]).then(([state, detected]) => {
        if (run === latest) {
          setView({ state, detected });
        }
      });
    }
    refresh();
    const unsubscribe = host.subscribe(refresh);
    return () => {
      latest += 1;
      unsubscribe();
    };
  }, [send, host]);

  return (
    <main className="sidepanel" aria-busy={view === null}>
      {view !== null && <Content view={view} send={send} />}
    </main>
  );
}
