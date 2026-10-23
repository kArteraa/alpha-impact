const AMOUNT_PATTERN = /^\d{1,13}([.,]\d{1,2})?$/;

export function parseAmount(raw: string): number | null {
  const compact = raw.replace(/\s/g, "");
  if (!AMOUNT_PATTERN.test(compact)) {
    return null;
  }
  const amount = Number(compact.replace(",", "."));
  return amount > 0 ? amount : null;
}

const KOPECK_DIGITS = 2;
const RUB_PLAIN = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 });
const RUB_KOPECKS = new Intl.NumberFormat("ru-RU", {
  minimumFractionDigits: KOPECK_DIGITS,
  maximumFractionDigits: KOPECK_DIGITS,
});

export const RUB = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" });
export const NUMBER = new Intl.NumberFormat("ru-RU");
export const RATE = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });
const COMPACT_RUB: Intl.NumberFormatOptions = {
  style: "currency",
  currency: "RUB",
  notation: "compact",
  maximumFractionDigits: 1,
};

export const RUB_COMPACT = new Intl.NumberFormat("ru-RU", COMPACT_RUB);
export const RUB_DELTA = new Intl.NumberFormat("ru-RU", { ...COMPACT_RUB, signDisplay: "exceptZero" });
export const PERCENT = new Intl.NumberFormat("ru-RU", { style: "percent", maximumFractionDigits: 0 });
export const SECONDS = new Intl.NumberFormat("ru-RU", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const RUB_WHOLE = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB", maximumFractionDigits: 0 });

export function formatRub(raw: string): string {
  const amount = parseAmount(raw);
  if (amount === null) {
    return raw;
  }
  return (Number.isInteger(amount) ? RUB_PLAIN : RUB_KOPECKS).format(amount);
}
