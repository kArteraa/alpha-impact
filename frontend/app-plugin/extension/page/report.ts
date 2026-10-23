import type { Send } from "../messages";
import { detectPage } from "./detect";
import { showNotice } from "./notice";

function shown(document: Document): Promise<void> {
  if (document.visibilityState === "visible") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    const onChange = () => {
      if (document.visibilityState === "visible") {
        document.removeEventListener("visibilitychange", onChange);
        resolve();
      }
    };
    document.addEventListener("visibilitychange", onChange);
  });
}

export async function reportPage(document: Document, url: string, send: Send, openPanel: () => void): Promise<void> {
  await shown(document);
  const detected = detectPage(document, url);
  if (detected !== null && (await send({ type: "page", detected }))) {
    showNotice(document, openPanel);
  }
}
