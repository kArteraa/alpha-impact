import type { Role } from "@alpha-impact/plugin";
import { createContext, useContext } from "react";

export interface Session {
  userId: string;
  role: Role;
}

export const SessionContext = createContext<Session | null>(null);

export function useSession(): Session {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession must be used inside RequireSession");
  }
  return value;
}
