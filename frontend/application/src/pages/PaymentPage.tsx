import { InsightPanel, mockResponses } from "@alpha-impact/plugin";

export function PaymentPage() {
  return (
    <section>
      <h1>Новый платёж</h1>
      <div className="page-grid">
        <div className="card">Форма платежа появится в задаче AH-10.</div>
        <InsightPanel
          actionContext={{ type: "payment", amount: 1500000, beneficiary_id: "cp_logistics_spb" }}
          role="cfo"
          response={mockResponses.cards}
        />
      </div>
    </section>
  );
}
