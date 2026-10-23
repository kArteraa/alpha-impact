import { Icon } from "./Icon";

export function Alert({ text }: { text: string }) {
  return (
    <p className="error" role="alert">
      <Icon name="alert" size={18} />
      {text}
    </p>
  );
}
