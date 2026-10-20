const ICON_SIZE = 16;

function Icon({ path, flip = false }: { path: string; flip?: boolean }) {
  return (
    <svg
      width={ICON_SIZE}
      height={ICON_SIZE}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={flip ? { transform: "rotate(180deg)" } : undefined}
    >
      <path d={path} />
    </svg>
  );
}

const THUMB = "M7 10v11H4V10h3zm0 0 4-8a2 2 0 0 1 2 2v4h6a2 2 0 0 1 2 2.3l-1.3 8A2 2 0 0 1 17.7 20H7";

export function ThumbUpIcon() {
  return <Icon path={THUMB} />;
}

export function ThumbDownIcon() {
  return <Icon path={THUMB} flip />;
}

export function CheckIcon() {
  return <Icon path="M5 12.5 10 17l9-10" />;
}
