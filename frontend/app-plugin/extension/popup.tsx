import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "../src/styles/tokens.css";

function Popup() {
  return (
    <main>
      <h1>Alpha Impact</h1>
      <p>Выбор компании и роли появится в задаче AH-35.</p>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Popup />
  </StrictMode>,
);
