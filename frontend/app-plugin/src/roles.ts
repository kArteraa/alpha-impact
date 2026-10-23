import type { Role } from "./types";

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Собственник",
  ceo: "Генеральный директор",
  cfo: "Финансовый директор",
  treasurer: "Казначей",
  chief_accountant: "Главный бухгалтер",
};

export const ROLES = Object.entries(ROLE_LABELS) as [Role, string][];
