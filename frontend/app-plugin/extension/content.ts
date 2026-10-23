import type { ContentRequest, PanelRequest, Send } from "./messages";
import { detectPage } from "./page/detect";
import { reportPage } from "./page/report";

const send = ((request) => chrome.runtime.sendMessage(request)) as Send;
const OPEN_PANEL: PanelRequest = { type: "open-panel" };

chrome.runtime.onMessage.addListener((request: ContentRequest, _sender, reply) => {
  if (request.type === "detect") {
    reply(detectPage(document, location.href));
  }
});

void reportPage(document, location.href, send, () => void chrome.runtime.sendMessage(OPEN_PANEL));
