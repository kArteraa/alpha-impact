import tokens from "../../src/styles/tokens.css?raw";
import styles from "./notice.css?raw";

const NOTICE_TEXT = "Alpha Impact: есть событие, важное для вашей компании";

function lightTokens(css: string): string {
  return css.slice(0, css.indexOf("}") + 1).replace(":root", ":host");
}

function button(document: Document, className: string, text: string, onClick: () => void): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = className;
  element.textContent = text;
  element.addEventListener("click", onClick);
  return element;
}

export function showNotice(document: Document, onOpen: () => void): void {
  const host = document.createElement("alpha-impact-notice");
  const root = host.attachShadow({ mode: "open" });
  const style = document.createElement("style");
  style.textContent = lightTokens(tokens) + styles;
  const notice = document.createElement("div");
  notice.className = "notice";
  notice.setAttribute("role", "status");
  const text = document.createElement("p");
  text.className = "notice-text";
  text.textContent = NOTICE_TEXT;
  const open = button(document, "notice-open", "Открыть", () => {
    host.remove();
    onOpen();
  });
  const close = button(document, "notice-close", "×", () => host.remove());
  close.setAttribute("aria-label", "Закрыть");
  notice.append(text, open, close);
  root.append(style, notice);
  document.documentElement.append(host);
}
