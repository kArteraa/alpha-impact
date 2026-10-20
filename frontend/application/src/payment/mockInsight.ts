import { type InterpretResponse, mockResponses } from "@alpha-impact/plugin";

const DEMO_CARDS_COUNTERPARTY = "cp_logistics_spb";

export function mockInsightFor(beneficiaryId: string): InterpretResponse {
  return beneficiaryId === DEMO_CARDS_COUNTERPARTY ? mockResponses.cards : mockResponses.silent;
}
