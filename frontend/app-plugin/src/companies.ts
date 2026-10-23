const COMPANY_NAMES: Record<string, string> = {
  U_1941: "ООО «Северный опт»",
  U_9250: "АО «СтройЛизинг»",
  U_44245: "ООО «Автомир Поволжье»",
  U_235754: "АО «Транзит Групп»",
};

export function companyName(id: string): string {
  return COMPANY_NAMES[id] ?? id;
}
