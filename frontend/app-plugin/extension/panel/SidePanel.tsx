import { useEffect, useState } from "react";
import { InsightPanel, type InterpretFetcher, type PageContext, type Role, useInterpret } from "../../src";
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

function shownAs({ state, detected }: View): string {
  const viewer = state.signedIn ? [state.userId, state.settings.clientId, state.settings.role] : null;
  return JSON.stringify([viewer, detected?.page.url ?? null]);
}

function sameView(previous: View | null, next: View): boolean {
  return previous !== null && shownAs(previous) === shownAs(next);
}

function PageInsight({ page, role, send }: { page: PageContext; role: Role; send: Send }) {
  const fetcher: InterpretFetcher = async () => {
    const reply = await send({ type: "interpret", page });
    if (!reply.ok) {
      throw new Error(reply.error);
    }
    return reply.value;
  };
  const insight = useInterpret(page, fetcher);
  return (
    <InsightPanel
      actionContext={page}
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
    return (
      <p className="sidepanel-note" role="status">
        Молчу: страница не похожа на статью, карточку контрагента, тендер или курс валют
      </p>
    );
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
          setView((previous) => (sameView(previous, { state, detected }) ? previous : { state, detected }));
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
