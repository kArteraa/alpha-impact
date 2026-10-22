const DAY_MS = 86_400_000;

export function daysUntil(isoDate: string, now: Date): number {
  return (Date.parse(isoDate) - Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())) / DAY_MS;
}
