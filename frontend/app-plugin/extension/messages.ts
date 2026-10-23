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

export type ExtensionState =
  | { signedIn: false }
  | { signedIn: true; userId: string; clients: string[]; settings: Settings };

export type WorkerRequest =
  | { type: "state" }
  | { type: "login"; userId: string }
  | { type: "logout" }
  | { type: "settings"; patch: SettingsPatch }
  | { type: "interpret"; page: PageContext };

export type WorkerError = "signed_out" | "setup" | "http" | "network";

export type Result<T> = { ok: true; value: T } | { ok: false; error: WorkerError; status?: number };

export type ReplyOf<R extends WorkerRequest> = R extends { type: "interpret" }
  ? Result<InterpretResponse>
  : R extends { type: "login" }
    ? Result<ExtensionState>
    : ExtensionState;

export type Send = <R extends WorkerRequest>(request: R) => Promise<ReplyOf<R>>;
