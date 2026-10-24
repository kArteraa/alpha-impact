import { companyOf } from "./companies";

const RISING = [
  0.86, 0.88, 0.87, 0.9, 0.91, 0.84, 0.85, 0.89, 0.92, 0.94, 0.93, 0.95, 0.97, 0.9, 0.91, 0.94, 0.96, 0.98, 0.97,
  0.99, 1.02, 0.95, 0.96, 0.98, 1.01, 1.03, 1.02, 0.99, 0.98, 1,
];

const EASING = [
  1.12, 1.1, 1.13, 1.09, 1.08, 1.11, 1.06, 1.05, 1.07, 1.04, 1.02, 1.06, 1.03, 1.01, 0.98, 1.02, 1, 0.97, 0.99, 1.03,
  1.01, 0.98, 0.96, 0.99, 1.02, 1, 0.97, 1.01, 0.99, 1,
];

function trail(clientId: string, shape: readonly number[]): number[] {
  const { balance } = companyOf(clientId);
  return shape.map((factor) => Math.round(balance * factor));
}

export const BALANCE_HISTORY: Record<string, number[]> = {
  U_1941: trail("U_1941", RISING),
  U_9250: trail("U_9250", EASING),
  U_44245: trail("U_44245", EASING),
  U_235754: trail("U_235754", RISING),
};
