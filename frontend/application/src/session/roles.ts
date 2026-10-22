import type { Role } from "@alpha-impact/plugin";

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Собственник",
  ceo: "Генеральный директор",
  cfo: "Финансовый директор",
  treasurer: "Казначей",
  chief_accountant: "Главный бухгалтер",
};

export const ROLE_FOCUS: Record<Role, string> = {
  owner: "Риски для бизнеса и стоимости компании",
  ceo: "Выручка, контрагенты и решения на ближайшие недели",
  cfo: "Ставки, кредиты, ликвидность и платёжный календарь",
  treasurer: "Остатки, курсы валют и размещение средств",
  chief_accountant: "Платежи, налоги и документы по сделкам",
};
