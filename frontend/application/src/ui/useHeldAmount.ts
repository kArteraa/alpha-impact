import { useState } from "react";
import { parseAmount } from "../money";

export function useHeldAmount(text: string): number | null {
  const [held, setHeld] = useState<number | null>(null);
  const amount = parseAmount(text);
  const next = text.trim() === "" || amount !== null ? amount : held;
  if (next !== held) {
    setHeld(next);
  }
  return next;
}
