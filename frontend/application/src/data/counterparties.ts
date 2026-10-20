export interface Counterparty {
  id: string;
  name: string;
  description: string;
}

export const COUNTERPARTIES: Counterparty[] = [
  { id: "cp_logistics_spb", name: "ООО «Северо-Западная логистика»", description: "Грузоперевозки, Санкт-Петербург" },
  { id: "cp_stationery", name: "ООО «Канцмир»", description: "Канцелярские товары, Москва" },
];
