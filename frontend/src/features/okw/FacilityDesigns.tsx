"use client";

import { useRouter } from "next/navigation";
import { Button } from "../../components/ui/button";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * Hand-off from a facility detail into Match a Design with this facility
 * pre-selected. Matching is intentional: the user picks a design and runs it.
 */
export function FacilityDesigns({ okwId }: { okwId: string }) {
  const router = useRouter();
  return (
    <section className={PANEL}>
      <h2 className={cn(SECTION_LABEL, "mb-2")}>Matching designs</h2>
      <p className="mb-4 text-sm text-muted-foreground">
        Find which catalog designs this facility can produce. You’ll pick a
        design and confirm facility filters on the Match page before anything
        runs.
      </p>
      <Button
        onClick={() =>
          router.push(`/match?okw_id=${encodeURIComponent(okwId)}`)
        }
      >
        Find matching designs →
      </Button>
    </section>
  );
}
