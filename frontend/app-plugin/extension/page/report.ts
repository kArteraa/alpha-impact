import type { Send } from "../messages";
import { detectPage } from "./detect";
import { showNotice } from "./notice";

export async function reportPage(document: Document, url: string, send: Send, openPanel: () => void): Promise<void> {
  const detected = detectPage(document, url);
  if (detected !== null && (await send({ type: "page", detected }))) {
    showNotice(document, openPanel);
  }
}
