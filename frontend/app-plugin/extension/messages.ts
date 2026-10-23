import type { InterpretResponse, PageContext, Role } from "../src";
import type { PageType } from "./config";

export interface Settings {
  clientId: string | null;
  role: Role | null;
  autoshow: Record<PageType, boolean>;
}

export type ExtensionState =
  | { signedIn: false }
  | { signedIn: true; userId: string; clients: string[]; settings: Settings };

export type WorkerRequest =
  | { type: "state" }
  | { type: "login"; userId: string }
  | { type: "logout" }
  | { type: "settings"; patch: Partial<Settings> }
  | { type: "interpret"; page: PageContext };

export type WorkerError = "signed_out" | "setup" | "http" | "network";

export type WorkerReply<T> = { ok: true; value: T } | { ok: false; error: WorkerError; status?: number };

export type ReplyValue<R extends WorkerRequest> = R extends { type: "interpret" } ? InterpretResponse : ExtensionState;

export type Send = <R extends WorkerRequest>(request: R) => Promise<WorkerReply<ReplyValue<R>>>;

export function stateOf(reply: WorkerReply<ExtensionState>): ExtensionState {
  return reply.ok ? reply.value : { signedIn: false };
}
