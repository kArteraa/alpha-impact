import { API_BASE } from "./config";
import type { WorkerRequest } from "./messages";
import { createApi } from "./worker/api";
import { chromeStore } from "./worker/store";
import { createWorker } from "./worker/worker";

const worker = createWorker({
  api: createApi(API_BASE, (url, init) => fetch(url, init)),
  session: chromeStore(chrome.storage.session),
  local: chromeStore(chrome.storage.local),
  now: Date.now,
});

chrome.runtime.onMessage.addListener((request: WorkerRequest, _sender, reply) => {
  void worker(request).then(reply);
  return true;
});
