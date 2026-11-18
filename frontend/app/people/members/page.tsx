"use client";

import { RequireCoordinator } from "@/features/auth/RequireAdmin";
import { PeoplePage } from "@/views/PeoplePage";

export default function Page() {
  return (
    <RequireCoordinator>
      <PeoplePage />
    </RequireCoordinator>
  );
}
