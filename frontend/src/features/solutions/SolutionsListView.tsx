"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { listSolutions, type SolutionSummary } from "../../api/ohm/supply-tree";
import {
  formatSaved,
  scorePercent,
  scoreVariant,
  solutionLabel,
} from "./solutionSummary";
import { PageHero, type CrumbTerm } from "../../components/layout/PageHero";
import { NetworkIllustration } from "../../components/ui/illustrations";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorMessage } from "../../components/ui/ErrorMessage";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { Badge } from "../../components/ui/Badge";
import { buttonVariants } from "../../components/ui/button";
import { PANEL, PANEL_INSET } from "../../components/ui/surface";
import {
  BODY_MUTED,
  CAPTION,
  CARD_TITLE,
} from "../../components/ui/typography";
import { useAuth } from "../../context/AuthContext";
import { cn } from "@/lib/utils";

/** Every term leads somewhere; this page has no aspect worth naming as text. */
const SOLUTIONS_CRUMB: readonly CrumbTerm[] = [
  { label: "match", href: "/match" },
  { label: "designs", href: "/okh" },
  { label: "facilities", href: "/facilities" },
];

function SolutionCard({ solution }: { solution: SolutionSummary }) {
  const percent = scorePercent(solution.score);
  const saved = formatSaved(solution.created_at);

  return (
    <Link
      href={`/visualization/${solution.id}`}
      className={cn(
        PANEL,
        "flex flex-col gap-2 no-underline transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h2 className={cn(CARD_TITLE, "min-w-0 break-words")}>
          {solutionLabel(solution)}
        </h2>
        {percent !== null && (
          <Badge variant={scoreVariant(percent)}>{percent}%</Badge>
        )}
      </div>

      {solution.facility_name && (
        <p className={BODY_MUTED}>{solution.facility_name}</p>
      )}

      <div className={cn(CAPTION, "flex flex-wrap gap-x-3 gap-y-1 font-mono")}>
        <span>
          {solution.facility_count} facilit
          {solution.facility_count === 1 ? "y" : "ies"}
        </span>
        <span>
          {solution.tree_count} tree{solution.tree_count === 1 ? "" : "s"}
        </span>
        {saved && <span>{saved}</span>}
      </div>
    </Link>
  );
}

/**
 * The caller's saved supply trees.
 *
 * This browse existed before and was removed for listing every visitor's
 * searches out of unscoped shared storage. It is back because the listing is
 * now scoped server-side to the account behind the API key — which is also why
 * the no-key state below says so plainly rather than showing an empty grid: an
 * anonymous reader has no history, and a page that implied their matches had
 * vanished would be describing the scoping as data loss.
 */
export function SolutionsListView() {
  const { token } = useAuth();
  // Fetched unconditionally, never gated on the token. Scoping is the server's
  // job — it answers an anonymous caller with an empty list — and a query that
  // only runs when a key is held is the same divergence demoMode.ts warns
  // against: demo mode swaps the data source at the fetch boundary and holds
  // no key, so an `enabled: !!token` here left the demo world permanently
  // showing "connect a key" over a world that needs none.
  //
  // The token still decides what an empty result MEANS, which is presentation
  // rather than a second code path.
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["solutions", token],
    queryFn: listSolutions,
    staleTime: 30_000,
  });

  const solutions = data ?? [];
  const isEmpty = !isLoading && !isError && solutions.length === 0;

  return (
    <div className="space-y-6">
      <PageHero
        title="Saved Solutions"
        crumb={SOLUTIONS_CRUMB}
        description="Supply trees saved from your matches. Only yours are listed."
      />

      {isLoading && (
        <div className={cn(PANEL_INSET, "p-8")}>
          <LoadingSpinner message="Loading solutions…" />
        </div>
      )}

      {isError && <ErrorMessage error={error} retry={() => refetch()} />}

      {/*
        One empty state, two readings of it. With no key the list is empty
        because nothing identifies you, not because nothing was saved — and
        "No saved solutions" there would report the scoping as data loss to
        someone whose matches are all still where they left them.
      */}
      {isEmpty &&
        (token ? (
          <EmptyState
            icon={() => <NetworkIllustration className="h-10 w-10" />}
            heading="No saved solutions"
            body="Run a match and its supply tree is saved here."
            action={
              <Link
                href="/match"
                className={cn(buttonVariants({ size: "lg" }), "no-underline")}
              >
                Match a design
              </Link>
            }
          />
        ) : (
          <EmptyState
            icon={() => <NetworkIllustration className="h-10 w-10" />}
            heading="Connect an API key to see your saved solutions"
            body="Saved solutions belong to the account that ran the match, so this list stays empty until a key identifies you."
            action={
              <Link
                href="/settings/session"
                className={cn(buttonVariants({ size: "lg" }), "no-underline")}
              >
                Open Session
              </Link>
            }
          />
        ))}

      {!isLoading && !isError && solutions.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {solutions.map((solution) => (
            <SolutionCard key={solution.id} solution={solution} />
          ))}
        </div>
      )}
    </div>
  );
}
