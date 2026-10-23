import { useEffect } from "react";
import { Navigate, Outlet, useNavigate } from "react-router";
import { onUnauthorized } from "../api/client";
import { SessionContext } from "./context";
import { forgetUser, loadRole, loadUser } from "./storage";

export function RequireSession() {
  const navigate = useNavigate();
  useEffect(
    () =>
      onUnauthorized(() => {
        forgetUser();
        navigate("/login", { replace: true });
      }),
    [navigate],
  );
  const userId = loadUser();
  const role = userId === null ? null : loadRole(userId);
  if (userId === null) {
    return <Navigate to="/login" replace />;
  }
  if (role === null) {
    return <Navigate to="/role" replace />;
  }
  return (
    <SessionContext.Provider value={{ userId, role }}>
      <Outlet />
    </SessionContext.Provider>
  );
}
