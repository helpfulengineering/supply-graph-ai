"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { PageHero } from "../../components/layout/PageHero";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { Badge } from "../../components/ui/Badge";
import { Button } from "../../components/ui/button";
import { PANEL } from "../../components/ui/surface";
import {
  SECTION_LABEL_SM,
  SECTION_TITLE,
} from "../../components/ui/typography";
import {
  CHECKBOX,
  CHECKBOX_HIT,
  FIELD,
  FIELD_SM,
  LABEL,
} from "../../components/ui/field";
import { useAuth } from "../../context/AuthContext";
import {
  fetchOkhList,
  setOkhVisibilityBulk,
  type BulkVisibilityResult,
  type VisibilityLevel,
} from "../../api/ohm/okh";
import { MyKeysPanel } from "./MyKeysPanel";
import { searchOkw, setOkwVisibilityBulk } from "../../api/ohm/okw";
import { VisibilityBadge } from "../okh/VisibilityBadge";
import { AUDIENCE, LEVELS } from "../okh/VisibilityControl";

const DESIGNS_KEY = ["okh-list", "account", "mine"] as const;
const FACILITIES_KEY = ["okw-search", "account", "mine"] as const;

/**
 * Where a signed-in visitor goes.
 *
 * Settings is admin-only and stays that way, so a registered non-admin needs
 * somewhere that is theirs: everything you have made, who can see each one,
 * and a way to change that for many at once (#576).
 *
 * The lists ask for `mine=true`. Without it a caller sees shareable records
 * plus their own, so their *shared* records are indistinguishable from anyone
 * else's and a section claiming to be all of yours would quietly miss half.
 */
export function AccountView() {
  const { token, user, isLoading, clear, sessionOrigin, signedIn } = useAuth();

  const designs = useQuery({
    queryKey: DESIGNS_KEY,
    queryFn: () => fetchOkhList({ page_size: 100, mine: true }),
    enabled: signedIn,
  });
  const facilities = useQuery({
    queryKey: FACILITIES_KEY,
    queryFn: () => searchOkw({ page_size: 100, mine: true }),
    enabled: signedIn,
  });

  if (!signedIn) {
    return (
      <>
        <PageHero title="Your account" />
        <EmptyState
          icon={UserPlus}
          heading="You are not signed in"
          body="Register on this node, or connect a key you already have."
          action={
            <div className="flex gap-3">
              <Link href="/register" className="text-sm underline">
                Register
              </Link>
              <Link href="/login" className="text-sm underline">
                Sign in
              </Link>
              <Link href="/settings/session" className="text-sm underline">
                Connect a key
              </Link>
            </div>
          }
        />
      </>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <>
      <PageHero title="Your account" />

      <div className="space-y-6">
        <section className={PANEL} aria-labelledby="account-identity">
          <h2 id="account-identity" className={SECTION_TITLE}>
            Identity
          </h2>
          {user ? (
            <dl className="mt-3 space-y-2 text-sm">
              <div>
                <dt className={SECTION_LABEL_SM}>Name</dt>
                <dd className="text-foreground">{user.name}</dd>
              </div>
              {user.subject_did && (
                <div>
                  <dt className={SECTION_LABEL_SM}>DID</dt>
                  <dd className="break-all font-mono text-xs text-foreground">
                    {user.subject_did}
                  </dd>
                </div>
              )}
              <div>
                <dt className={`${SECTION_LABEL_SM} mb-1.5`}>Permissions</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {user.permissions.map((p) => (
                    <Badge key={p} variant={p === "admin" ? "indigo" : "blue"}>
                      {p}
                    </Badge>
                  ))}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-sm text-muted-foreground">
              Signed in, but this node did not return an identity.
            </p>
          )}
          {/* Both "why am I still signed in" and "why am I not" need a visible
              answer, or persistence reads as a bug in whichever direction
              surprises you. */}
          <p className="mt-4 text-sm text-muted-foreground">
            {!token
              ? "You stay signed in on this browser until you sign out, you are idle for 30 days, or 90 days pass."
              : sessionOrigin === "minted"
                ? "You stay signed in on this device until you sign out or the key expires."
                : "You are signed in for this tab only, because this key was pasted in. Close the tab and it is gone."}
          </p>
          <button
            type="button"
            onClick={clear}
            className={`${FIELD_SM} mt-3 font-medium hover:bg-background dark:hover:bg-muted`}
          >
            Sign out
          </button>
        </section>

        <MyKeysPanel />

        <YourRecordsSection
          id="designs"
          title="Your designs"
          nouns={{ one: "design", many: "designs" }}
          browseHref="/okh"
          listKey={DESIGNS_KEY}
          loading={designs.isPending}
          rows={(designs.data?.items ?? []).map((d) => ({
            id: String(d.id),
            label: d.title ?? String(d.id),
            href: `/okh/${d.id}`,
            visibility: d.visibility,
          }))}
          nothing="You have not created a design yet."
          apply={setOkhVisibilityBulk}
        />

        <YourRecordsSection
          id="facilities"
          title="Your facilities"
          nouns={{ one: "facility", many: "facilities" }}
          browseHref="/facilities"
          listKey={FACILITIES_KEY}
          loading={facilities.isPending}
          rows={(facilities.data?.results ?? []).map((f) => ({
            id: String(f.id),
            label: f.name ?? String(f.id),
            href: `/facilities/${f.id}`,
            visibility: f.visibility,
          }))}
          nothing="You have not created a facility yet."
          apply={setOkwVisibilityBulk}
        />
      </div>
    </>
  );
}

const OUTCOME: Record<BulkVisibilityResult["outcome"], string> = {
  changed: "Changed",
  not_yours: "Not yours",
  not_found: "Not found",
};

function YourRecordsSection({
  id,
  title,
  nouns,
  browseHref,
  listKey,
  loading,
  rows,
  nothing,
  apply,
}: {
  id: string;
  title: string;
  nouns: { one: string; many: string };
  browseHref: string;
  /** The list query to refetch once a change lands, so badges catch up. */
  listKey: readonly unknown[];
  loading: boolean;
  rows: {
    id: string;
    label: string;
    href: string;
    visibility?: VisibilityLevel;
  }[];
  nothing: string;
  apply: (
    ids: string[],
    level: VisibilityLevel,
  ) => Promise<BulkVisibilityResult[]>;
}) {
  const { hasWrite, reportAuthFailure } = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string[]>([]);
  const [level, setLevel] = useState<VisibilityLevel | null>(null);
  const [outcomes, setOutcomes] = useState<
    Record<string, BulkVisibilityResult["outcome"]>
  >({});

  const mutation = useMutation({
    mutationFn: (to: VisibilityLevel) => apply(selected, to),
    onSuccess: (results) => {
      setOutcomes(Object.fromEntries(results.map((r) => [r.id, r.outcome])));
      setSelected([]);
      setLevel(null);
      void queryClient.invalidateQueries({ queryKey: listKey });
    },
    onError: reportAuthFailure,
  });

  const toggle = (rowId: string) =>
    setSelected((s) =>
      s.includes(rowId) ? s.filter((x) => x !== rowId) : [...s, rowId],
    );
  const count = selected.length;
  const pending = count > 0 && level;

  return (
    <section className={PANEL} aria-labelledby={`yours-${id}`}>
      <h2 id={`yours-${id}`} className={SECTION_TITLE}>
        {title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Everything you created, whoever can see it. New records start private.
      </p>

      {loading ? (
        <div className="py-6">
          <LoadingSpinner />
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          {nothing}{" "}
          <Link href={browseHref} className="underline">
            Browse
          </Link>
        </p>
      ) : (
        <>
          <ul className="mt-3 space-y-1">
            {rows.map((row) => (
              <li key={row.id} className="flex items-center gap-3 text-sm">
                <label className={CHECKBOX_HIT}>
                  <input
                    type="checkbox"
                    className={CHECKBOX}
                    aria-label={`Select ${row.label}`}
                    checked={selected.includes(row.id)}
                    disabled={!hasWrite || mutation.isPending}
                    onChange={() => toggle(row.id)}
                  />
                </label>
                <Link
                  href={row.href}
                  className="block min-w-0 truncate py-0.5 underline"
                >
                  {row.label}
                </Link>
                <VisibilityBadge level={row.visibility} />
                {outcomes[row.id] && (
                  <span className="text-xs text-muted-foreground">
                    {OUTCOME[outcomes[row.id]]}
                  </span>
                )}
              </li>
            ))}
          </ul>

          <label className={`${LABEL} mt-4`}>
            <span className="sr-only">
              New visibility for selected {nouns.many}
            </span>
            <select
              value={level ?? ""}
              disabled={!hasWrite || count === 0 || mutation.isPending}
              onChange={(e) =>
                setLevel((e.target.value || null) as VisibilityLevel | null)
              }
              className={`${FIELD} w-full max-w-xs`}
            >
              <option value="">Change visibility of selected…</option>
              {LEVELS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
          </label>

          {pending && (
            <div className="mt-3 space-y-2 text-sm" role="status">
              <p className="text-foreground">
                <span className="font-medium">Who will see these: </span>
                {AUDIENCE[level]}
              </p>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() => mutation.mutate(level)}
                >
                  {mutation.isPending
                    ? "Applying…"
                    : `Apply ${level} to ${count} ${count === 1 ? nouns.one : nouns.many}`}
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={mutation.isPending}
                  onClick={() => setLevel(null)}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
          {!hasWrite && (
            <p className="mt-2 text-xs text-muted-foreground">
              Changing visibility requires a write-capable API key.
            </p>
          )}
          {mutation.isError && (
            <p className="mt-2 text-sm text-destructive" role="alert">
              {mutation.error instanceof Error
                ? mutation.error.message
                : "Update failed."}
            </p>
          )}
        </>
      )}
    </section>
  );
}
