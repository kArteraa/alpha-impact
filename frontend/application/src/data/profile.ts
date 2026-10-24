export type FeatureGroup = "company" | "geography" | "scale" | "bank";

export interface FeatureSpec {
  group: FeatureGroup;
  labels?: Record<string, string>;
  editable?: boolean;
  money?: boolean;
}

export const FEATURE_GROUPS: readonly (readonly [FeatureGroup, string])[] = [
  ["company", "Компания"],
  ["geography", "География"],
  ["scale", "Масштаб"],
  ["bank", "Отношения с банком"],
];

const INDUSTRIES: Record<string, string> = {
  wholesale: "Оптовая торговля",
  retail: "Розничная торговля",
  logistics: "Логистика",
  construction: "Строительство",
  real_estate: "Недвижимость",
  auto_dealer: "Автодилеры",
  agro: "Сельское хозяйство",
  food: "Пищевая промышленность",
  chemicals: "Химия",
  pharma: "Фармацевтика",
  energy: "Энергетика",
  fuel: "Топливо",
  horeca: "Гостиницы и общепит",
  it: "ИТ",
  finance: "Финансы",
  leasing: "Лизинг",
  other: "Другое",
};

const PRODUCTS: Record<string, string> = {
  settlement: "Расчётный счёт",
  guarantee: "Гарантия",
  loan: "Кредит",
  leasing: "Лизинг",
  deposit: "Депозит",
  payroll: "Зарплатный проект",
  factoring: "Факторинг",
};

const CLIENT_TYPES: Record<string, string> = {
  CLIENT: "Действующий клиент",
  CLOSE_CLIENT: "Закрытый клиент",
};

export const FEATURES: Record<string, FeatureSpec> = {
  industry_class: { group: "company", labels: INDUSTRIES, editable: true },
  okved_name: { group: "company" },
  okved_code: { group: "company" },
  company_age: { group: "company" },
  eco_stage: { group: "company" },
  ownership: { group: "company" },
  region: { group: "geography" },
  city: { group: "geography" },
  import_countries: { group: "geography" },
  revenue_rub: { group: "scale", money: true },
  workers: { group: "scale" },
  cl_type: { group: "bank", labels: CLIENT_TYPES },
  products: { group: "bank", labels: PRODUCTS },
};
