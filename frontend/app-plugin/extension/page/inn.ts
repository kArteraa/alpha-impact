const CANDIDATE = /(?<![0-9A-Za-z_])(?:[0-9]{12}|[0-9]{10})(?![0-9A-Za-z_])/g;
const WEIGHTS = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8];
const CHECK_POSITIONS: Record<number, number[]> = { 10: [9], 12: [10, 11] };
const NO_REGION = "00";
const PERSON_INN_LENGTH = 12;
const HIDDEN_INN = "ИНН скрыт";

function checkDigit(digits: string): string {
  const weights = WEIGHTS.slice(-digits.length);
  const total = [...digits].reduce((sum, digit, index) => sum + Number(digit) * weights[index], 0);
  return String((total % 11) % 10);
}

function validInn(value: string): boolean {
  return (
    !value.startsWith(NO_REGION) && CHECK_POSITIONS[value.length].every((n) => value[n] === checkDigit(value.slice(0, n)))
  );
}

export function innsIn(text: string): string[] {
  return Array.from(text.matchAll(CANDIDATE), ([value]) => value).filter(validInn);
}

export function hidePersonInns(text: string): string {
  return text.replace(CANDIDATE, (value) => (value.length === PERSON_INN_LENGTH && validInn(value) ? HIDDEN_INN : value));
}
