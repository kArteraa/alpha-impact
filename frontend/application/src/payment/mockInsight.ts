import { type InterpretResponse, mockResponses, type PaymentContext } from "@alpha-impact/plugin";

const DEMO_CARDS_COUNTERPARTY = "cp_logistics_spb";

export function mockInsightFor(beneficiaryId: PaymentContext["beneficiary_id"]): InterpretResponse {
  return beneficiaryId === DEMO_CARDS_COUNTERPARTY ? mockResponses.cards : mockResponses.silent;
}
