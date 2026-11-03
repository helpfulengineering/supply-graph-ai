"use client";

import { RequireCoordinator } from "@/features/auth/RequireAdmin";
import { SettingsPage } from "@/views/SettingsPage";

export default function Page() {
  return (
    <RequireCoordinator>
      <SettingsPage />
    </RequireCoordinator>
  );
}
