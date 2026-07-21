import { Outlet } from "react-router-dom";
import { NavBar } from "./NavBar";
import { AuthBanner } from "../../features/auth/AuthBanner";

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <NavBar />
      <AuthBanner />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
