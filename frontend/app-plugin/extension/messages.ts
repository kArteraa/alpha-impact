import type { InterpretResponse, PageContext, Role } from "../src";
import type { PageType } from "./config";

export type Autoshow = Record<PageType, boolean>;

export interface Settings {
  clientId: string | null;
  role: Role | null;
  autoshow: Autoshow;
}

export interface SettingsPatch {
  clientId?: string | null;
  role?: Role | null;
  autoshow?: Partial<Autoshow>;
}

export interface DetectedPage {
  pageType: PageType;
  page: PageContext;
}

export type ExtensionState =
  | { signedIn: false }
  | { signedIn: true; userId: string; clients: string[]; settings: Settings };

export type WorkerRequest =
  | { type: "state" }
  | { type: "login"; userId: string }
  | { type: "logout" }
  | { type: "settings"; patch: SettingsPatch }
  | { type: "interpret"; page: PageContext }
  | { type: "page"; detected: DetectedPage };

export type ContentRequest = { type: "detect" };

export type PanelRequest = { type: "open-panel" };

export type WorkerError = "signed_out" | "setup" | "http" | "network" | "failed";

export type Result<T> = { ok: true; value: T } | { ok: false; error: WorkerError; status?: number };

export interface WorkerReplies {
  state: ExtensionState;
  login: Result<ExtensionState>;
  logout: ExtensionState;
  settings: ExtensionState;
  interpret: Result<InterpretResponse>;
  page: boolean;
}

export type ReplyOf<R extends WorkerRequest> = WorkerReplies[R["type"]];

export type Send = <R extends WorkerRequest>(request: R) => Promise<ReplyOf<R>>;
