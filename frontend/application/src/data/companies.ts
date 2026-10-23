import { companyName } from "@alpha-impact/plugin";

export interface Company {
  id: string;
  name: string;
  account: string;
  balance: number;
}

const SHOWCASE: Record<string, Pick<Company, "account" | "balance">> = {
  U_1941: { account: "·· 4417", balance: 48_250_300 },
  U_9250: { account: "·· 9032", balance: 126_480_000 },
  U_44245: { account: "·· 2768", balance: 37_910_000 },
  U_235754: { account: "·· 5120", balance: 15_600_000 },
};

export function companyOf(id: string): Company {
  return { id, name: companyName(id), ...(SHOWCASE[id] ?? { account: "", balance: 0 }) };
}
