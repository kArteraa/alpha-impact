import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";
import "@alpha-impact/plugin/tokens.css";
import "@alpha-impact/plugin/controls.css";
import "./styles/base.css";
import "./styles/layout.css";
import "./styles/forms.css";
import "./styles/controls.css";
import "./styles/charts.css";
import "./styles/pages.css";
import "./styles/trace.css";
import "./styles/auth.css";
import "./styles/states.css";
import "./styles/dashboard.css";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
