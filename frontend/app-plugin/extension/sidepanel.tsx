import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/styles/tokens.css";
import "./sidepanel.css";
import type { ContentRequest, DetectedPage, Send, WorkerRequest } from "./messages";
import { type PanelHost, SidePanel } from "./panel/SidePanel";

const send = ((request) => chrome.runtime.sendMessage(request)) as Send;
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
    const onPage = (request: WorkerRequest) => {
      if (request.type === "page") {
        listener();
      }
    };
    const onLoaded = (_tabId: number, change: chrome.tabs.OnUpdatedInfo) => {
      if (change.status === "complete") {
        listener();
      }
    };
    chrome.tabs.onActivated.addListener(listener);
    chrome.tabs.onUpdated.addListener(onLoaded);
    chrome.runtime.onMessage.addListener(onPage);
    chrome.storage.onChanged.addListener(listener);
    return () => {
      chrome.tabs.onActivated.removeListener(listener);
      chrome.tabs.onUpdated.removeListener(onLoaded);
      chrome.runtime.onMessage.removeListener(onPage);
      chrome.storage.onChanged.removeListener(listener);
    };
  },
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SidePanel send={send} host={host} />
  </StrictMode>,
);
