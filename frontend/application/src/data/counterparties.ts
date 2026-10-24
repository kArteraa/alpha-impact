export interface Counterparty {
  id: string;
  name: string;
  description: string;
}

export const COUNTERPARTIES: Counterparty[] = [
  { id: "U_96105", name: "ООО «Северо-Западная логистика»", description: "Грузоперевозки, Санкт-Петербург" },
  { id: "U_22524", name: "ООО «Канцмир»", description: "Канцелярские товары, Москва" },
];
