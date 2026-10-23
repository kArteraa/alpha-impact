import type { InterpretFetcher } from "@alpha-impact/plugin";
import { api } from "../api/client";
import { useCompany } from "../company/context";
import { useSession } from "../session/context";

export function useInterpretFetcher(): InterpretFetcher {
  const { company } = useCompany();
  const { userId, role } = useSession();
  return (action, signal) =>
    api.interpret({ user_id: userId, client_id: company.id, role, action_context: action }, signal);
}
