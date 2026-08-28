"use client";

import { RequireAdmin } from "./RequireAdmin";
import { SettingsPage } from "../../views/SettingsPage";

/** Every admin settings tab is the same guarded page; tabs dispatch on pathname. */
export function AdminSettings() {
  return (
    <RequireAdmin>
      <SettingsPage />
    </RequireAdmin>
  );
}
