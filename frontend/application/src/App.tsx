import { Showcase } from "@alpha-impact/plugin/showcase";
import { Route, Routes } from "react-router";
import { Layout } from "./Layout";
import { DashboardPage } from "./pages/DashboardPage";
import { DepositPage } from "./pages/DepositPage";
import { EventPage } from "./pages/EventPage";
import { EventsPage } from "./pages/EventsPage";
import { LoansPage } from "./pages/LoansPage";
import { LoginPage } from "./pages/LoginPage";
import { PaymentPage } from "./pages/PaymentPage";
import { ProfilePage } from "./pages/ProfilePage";
import { RolePage } from "./pages/RolePage";
import { TracePage } from "./pages/TracePage";
import { RequireSession } from "./session/RequireSession";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/role" element={<RolePage />} />
      <Route path="/showcase" element={<Showcase />} />
      <Route element={<RequireSession />}>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/events/:id" element={<EventPage />} />
          <Route path="/payments/new" element={<PaymentPage />} />
          <Route path="/deposits/new" element={<DepositPage />} />
          <Route path="/loans" element={<LoansPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/trace/:id" element={<TracePage />} />
        </Route>
      </Route>
    </Routes>
  );
}
