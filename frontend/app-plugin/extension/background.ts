import { API_BASE } from "./config";
import type { PanelRequest, WorkerRequest } from "./messages";
import { createApi } from "./worker/api";
import { chromeStore } from "./worker/store";
import { createWorker } from "./worker/worker";

const worker = createWorker({
  api: createApi(API_BASE, fetch),
  session: chromeStore(chrome.storage.session),
  local: chromeStore(chrome.storage.local),
  now: Date.now,
});

function fromExtension(sender: chrome.runtime.MessageSender): boolean {
  return sender.url?.startsWith(chrome.runtime.getURL("")) === true;
}

chrome.runtime.onMessage.addListener((request: WorkerRequest | PanelRequest, sender, reply) => {
  if (request.type === "open-panel") {
    if (sender.tab?.id !== undefined) {
      void chrome.sidePanel.open({ tabId: sender.tab.id });
    }
    return false;
  }
  if (request.type !== "page" && !fromExtension(sender)) {
    return false;
  }
  void worker(request).then(reply);
  return true;
});
