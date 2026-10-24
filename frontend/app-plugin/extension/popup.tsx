import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/styles/tokens.css";
import "../src/styles/controls.css";
import "./popup/popup.css";
import { Popup } from "./popup/Popup";
import { send } from "./send";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Popup send={send} />
  </StrictMode>,
);
