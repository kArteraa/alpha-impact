import { type ReactNode, useId } from "react";
import { mockResponses } from "../mocks";
import { ClaimTypeBadge } from "../panel/ClaimTypeBadge";
import { InsightPanel } from "../panel/InsightPanel";
import type { ActionContext, ClaimType } from "../types";
import "./showcase.css";

const CONTEXT: ActionContext = { type: "payment", amount: 1_500_000, beneficiary_id: "cp_logistics_spb" };
const DEPOSIT: ActionContext = { type: "deposit", amount: 50_000_000, term_days: 360 };
const CLAIM_TYPES: ClaimType[] = ["fact", "bank", "ai"];
const WIDTHS = [
  { width: 400, compact: false },
  { width: 320, compact: true },
] as const;

function Section({ title, children }: { title: string; children: ReactNode }) {
  const headingId = useId();
  return (
    <section className="showcase-section" aria-labelledby={headingId}>
      <h2 id={headingId}>{title}</h2>
      {children}
    </section>
  );
}

function Frame({ label, children }: { label: string; children: ReactNode }) {
  return (
    <figure className="showcase-frame">
      <figcaption>{label}</figcaption>
      {children}
    </figure>
  );
}

export function Showcase() {
  return (
    <main className="showcase">
      <h1>Витрина InsightPanel</h1>
      <Section title="Пометки тезисов">
        <div className="showcase-badges">
          {CLAIM_TYPES.map((type) => (
            <ClaimTypeBadge key={type} type={type} />
          ))}
        </div>
      </Section>
      <Section title="Состояния">
        <div className="showcase-grid">
          <Frame label="Проверяю">
            <InsightPanel actionContext={CONTEXT} role="cfo" />
          </Frame>
          <Frame label="Ничего важного">
            <InsightPanel actionContext={CONTEXT} role="cfo" response={mockResponses.silent} />
          </Frame>
          <Frame label="Не успел">
            <InsightPanel actionContext={CONTEXT} role="cfo" failed onRetry={() => undefined} />
          </Frame>
          <Frame label="Обновляется поверх старой карточки">
            <InsightPanel actionContext={CONTEXT} role="cfo" response={mockResponses.cards} pending />
          </Frame>
        </div>
      </Section>
      <Section title="Карточка в двух контейнерах">
        <div className="showcase-widths">
          {WIDTHS.map(({ width, compact }) => (
            <div key={width} className="showcase-width" data-width={width} style={{ width }}>
              <Frame label={compact ? `${width} px · side panel, compact` : `${width} px · рядом с формой`}>
                <InsightPanel
                  actionContext={CONTEXT}
                  role="cfo"
                  response={mockResponses.cards}
                  compact={compact}
                  onFollowup={() => undefined}
                  onFeedback={async () => undefined}
                />
              </Frame>
            </div>
          ))}
        </div>
      </Section>
      <Section title="Карточка с расчётом">
        <div className="showcase-width" style={{ width: WIDTHS[0].width }}>
          <Frame label={`${WIDTHS[0].width} px · депозит`}>
            <InsightPanel actionContext={DEPOSIT} role="cfo" response={mockResponses.rates} />
          </Frame>
        </div>
      </Section>
    </main>
  );
}
