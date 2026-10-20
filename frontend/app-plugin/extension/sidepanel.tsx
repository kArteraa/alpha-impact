import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { InsightPanel } from "../src";
import { mockResponses } from "../src/mocks";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <InsightPanel
      actionContext={{ type: "page", url: "", text: "" }}
      role="cfo"
      response={mockResponses.cards}
    />
  </StrictMode>,
);
