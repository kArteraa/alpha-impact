export type FeatureGroup = "company" | "geography" | "scale" | "bank";

export interface FeatureSpec {
  label: string;
  group: FeatureGroup;
  options?: Record<string, string>;
  labels?: Record<string, string>;
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
  industry_class: { label: "Отрасль", group: "company", options: INDUSTRIES },
  okved_name: { label: "Основной вид деятельности", group: "company" },
  okved_code: { label: "Код ОКВЭД", group: "company" },
  company_age: { label: "Возраст компании, лет", group: "company" },
  eco_stage: { label: "Стадия развития", group: "company" },
  ownership: { label: "Форма собственности", group: "company" },
  region: { label: "Регион", group: "geography" },
  city: { label: "Город", group: "geography" },
  import_countries: { label: "Страны импорта", group: "geography" },
  revenue_rub: { label: "Выручка", group: "scale", money: true },
  workers: { label: "Сотрудников", group: "scale" },
  cl_type: { label: "Статус клиента", group: "bank", labels: CLIENT_TYPES },
  products: { label: "Продукты банка", group: "bank", labels: PRODUCTS },
};
