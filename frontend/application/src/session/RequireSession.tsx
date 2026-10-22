import { Navigate, Outlet } from "react-router";
import { SessionContext } from "./context";
import { loadRole, loadUser } from "./storage";

export function RequireSession() {
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
