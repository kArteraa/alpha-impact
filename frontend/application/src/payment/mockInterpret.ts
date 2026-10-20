import { type InterpretFetcher, mockResponses } from "@alpha-impact/plugin";

const DEMO_CARDS_COUNTERPARTY = "cp_logistics_spb";

export const mockInterpret: InterpretFetcher = (context) =>
  Promise.resolve(
    "beneficiary_id" in context && context.beneficiary_id === DEMO_CARDS_COUNTERPARTY
      ? mockResponses.cards
      : mockResponses.silent,
  );
