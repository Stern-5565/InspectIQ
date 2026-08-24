/**
 * The authenticated app shell: sidebar + header around whatever the current route renders.
 * Used as a layout route in App.jsx, nested inside ProtectedRoute so it only ever renders for
 * a logged-in user (Header assumes `user` is non-null - see useAuth()).
 *
 * One shell, not PROJECT_PLAN.md §6's separate desktop/mobile layout components yet - that
 * split matters once there's a genuinely different "field" (inspector-on-a-phone) vs.
 * "management" (dashboard/reports/admin on a desktop) navigation pattern to express, but with
 * only Dashboard built so far there's nothing to differentiate. Sidebar/Header are already
 * their own components specifically so that split is a later change to two files, not a
 * rewrite of this one.
 */
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />
      <div className="app-shell__main">
        <Header onToggleSidebar={() => setSidebarOpen((open) => !open)} />
        <main className="app-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
