export interface Company {
  id: string;
  name: string;
  account: string;
  balance: number;
}

const SHOWCASE: Record<string, Omit<Company, "id">> = {
  U_1941: { name: "ООО «Северный опт»", account: "·· 4417", balance: 48_250_300 },
  U_9250: { name: "АО «СтройЛизинг»", account: "·· 9032", balance: 126_480_000 },
  U_44245: { name: "ООО «Автомир Поволжье»", account: "·· 2768", balance: 37_910_000 },
  U_235754: { name: "АО «Транзит Групп»", account: "·· 5120", balance: 15_600_000 },
};

export function companyOf(id: string): Company {
  return { id, ...(SHOWCASE[id] ?? { name: id, account: "", balance: 0 }) };
}
