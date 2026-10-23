import type { Send } from "./messages";

export const send = ((request) => chrome.runtime.sendMessage(request)) as Send;
