interface PluralForms {
  one: string;
  few: string;
  many: string;
}

const RULES = new Intl.PluralRules("ru-RU");

export const DAYS: PluralForms = { one: "день", few: "дня", many: "дней" };

export function plural(count: number, forms: PluralForms): string {
  const rule = RULES.select(count);
  const word = rule === "one" ? forms.one : rule === "few" ? forms.few : forms.many;
  return `${count} ${word}`;
}
