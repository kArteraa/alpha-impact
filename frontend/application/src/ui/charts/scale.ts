export type Point = [number, number];

export function linePoints(values: readonly number[], width: number, height: number, inset: number): Point[] {
  const min = Math.min(...values);
  const span = Math.max(...values) - min;
  const step = values.length > 1 ? (width - 2 * inset) / (values.length - 1) : 0;
  const usable = height - 2 * inset;
  return values.map((value, index) => [
    inset + index * step,
    span === 0 ? height / 2 : inset + usable - ((value - min) / span) * usable,
  ]);
}

export function linePath(points: readonly Point[]): string {
  return points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x} ${y}`).join("");
}

export function areaPath(points: readonly Point[], height: number): string {
  const first = points[0];
  const last = points[points.length - 1];
  return `${linePath(points)}L${last[0]} ${height}L${first[0]} ${height}Z`;
}

export function ratio(value: number, max: number): number {
  return max > 0 ? value / max : 0;
}

export function shares(values: readonly number[]): number[] {
  const total = values.reduce((sum, value) => sum + value, 0);
  return values.map((value) => (total > 0 ? (value / total) * 100 : 0));
}
