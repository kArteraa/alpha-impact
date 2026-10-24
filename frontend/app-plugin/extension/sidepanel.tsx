import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/styles/tokens.css";
import "./sidepanel.css";
import type { ContentRequest, DetectedPage, WorkerRequest } from "./messages";
import { type PanelHost, SidePanel } from "./panel/SidePanel";
import { send } from "./send";
import { CACHE_KEY } from "./worker/cache";

const DETECT: ContentRequest = { type: "detect" };

const host: PanelHost = {
  async activePage() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.id === undefined) {
      return null;
    }
    try {
      return await chrome.tabs.sendMessage<ContentRequest, DetectedPage | null>(tab.id, DETECT);
    } catch {
      return null;
    }
  },
  subscribe(listener) {
    const onPage = (request: WorkerRequest, sender: chrome.runtime.MessageSender) => {
      if (request.type === "page" && sender.tab?.active === true) {
        listener();
      }
    };
    const onLoaded = (_tabId: number, change: chrome.tabs.OnUpdatedInfo, tab: chrome.tabs.Tab) => {
      if (change.status === "complete" && tab.active) {
        listener();
      }
    };
    const onStored = (changes: Record<string, chrome.storage.StorageChange>) => {
      if (Object.keys(changes).some((key) => key !== CACHE_KEY)) {
        listener();
      }
    };
    chrome.tabs.onActivated.addListener(listener);
    chrome.tabs.onUpdated.addListener(onLoaded);
    chrome.runtime.onMessage.addListener(onPage);
    chrome.storage.onChanged.addListener(onStored);
    return () => {
      chrome.tabs.onActivated.removeListener(listener);
      chrome.tabs.onUpdated.removeListener(onLoaded);
      chrome.runtime.onMessage.removeListener(onPage);
      chrome.storage.onChanged.removeListener(onStored);
    };
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SidePanel send={send} host={host} />
  </StrictMode>,
);
