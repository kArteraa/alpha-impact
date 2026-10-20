export interface Company {
  id: string;
  name: string;
  account: string;
  balance: number;
}

export const COMPANIES: Company[] = [
  { id: "client_wholesale", name: "ООО «Северный опт»", account: "·· 4417", balance: 48_250_300 },
  { id: "client_construction", name: "АО «СтройЛизинг»", account: "·· 9032", balance: 126_480_000 },
];
