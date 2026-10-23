import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/styles/tokens.css";
import "../src/styles/controls.css";
import "./popup/popup.css";
import type { Send } from "./messages";
import { Popup } from "./popup/Popup";

const send = ((request) => chrome.runtime.sendMessage(request)) as Send;

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Popup send={send} />
  </StrictMode>,
);
