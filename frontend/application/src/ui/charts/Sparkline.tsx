import { areaPath, linePath, linePoints } from "./scale";

const WIDTH = 240;
const HEIGHT = 56;
const INSET = 4;

export function Sparkline({ values, label, className }: { values: readonly number[]; label: string; className?: string }) {
  const points = linePoints(values, WIDTH, HEIGHT, INSET);
  return (
    <svg
      className={className ? `sparkline ${className}` : "sparkline"}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="none"
      role="img"
      aria-label={label}
    >
      <path className="sparkline-area" d={areaPath(points, HEIGHT)} />
      <path className="sparkline-line" d={linePath(points)} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}
