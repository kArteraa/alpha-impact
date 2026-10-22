export interface FeatureSpec {
  label: string;
  options?: Record<string, string>;
}

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

export const FEATURES: Record<string, FeatureSpec> = {
  industry_class: { label: "Отрасль", options: INDUSTRIES },
  okved_name: { label: "Основной вид деятельности" },
  okved_code: { label: "Код ОКВЭД" },
  region: { label: "Регион" },
  city: { label: "Город" },
  revenue_rub: { label: "Выручка, ₽" },
  workers: { label: "Сотрудников" },
  company_age: { label: "Возраст компании, лет" },
  eco_stage: { label: "Стадия развития" },
  ownership: { label: "Форма собственности" },
  cl_type: { label: "Статус клиента" },
  products: { label: "Продукты банка" },
  import_countries: { label: "Страны импорта" },
};
