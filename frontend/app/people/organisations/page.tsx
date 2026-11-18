"use client";

import { RequireSignedIn } from "@/features/auth/RequireAdmin";
import { PeoplePage } from "@/views/PeoplePage";

export default function Page() {
  return (
    <RequireSignedIn>
      <PeoplePage />
    </RequireSignedIn>
  );
}
