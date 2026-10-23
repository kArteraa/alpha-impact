import type { ContentRequest, PanelRequest } from "./messages";
import { detectPage } from "./page/detect";
import { reportPage } from "./page/report";
import { send } from "./send";

const OPEN_PANEL: PanelRequest = { type: "open-panel" };

chrome.runtime.onMessage.addListener((request: ContentRequest, _sender, reply) => {
  if (request.type === "detect") {
    reply(detectPage(document, location.href));
  }
});

void reportPage(document, location.href, send, () => void chrome.runtime.sendMessage(OPEN_PANEL));
