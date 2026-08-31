"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { EyeOff, UserPlus } from "lucide-react";
import { PageHero } from "../../components/layout/PageHero";
import { LoadingSpinner } from "../../components/ui/LoadingSpinner";
import { EmptyState } from "../../components/ui/EmptyState";
import { Badge } from "../../components/ui/Badge";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL_SM, SECTION_TITLE } from "../../components/ui/typography";
import { FIELD_SM } from "../../components/ui/field";
import { useAuth } from "../../context/AuthContext";
import { fetchOkhList } from "../../api/ohm/okh";
import { MyKeysPanel } from "./MyKeysPanel";
import { searchOkw } from "../../api/ohm/okw";

/**
 * Where a signed-in visitor goes.
 *
 * Settings is admin-only and stays that way, so a registered non-admin needs
 * somewhere that is theirs. Its job is the one thing the CLI could do and the
 * UI could not: show you what you have made that nobody else can see, and get
 * you from there to shared.
 *
 * "Unshared" is exactly derivable from the list payload, and deliberately not
 * called "everything you made": a caller sees shareable records plus their
 * own, so a non-shareable row is necessarily theirs — but their *shared*
 * records are indistinguishable from anyone else's, and a section that claimed
 * to be all of yours would quietly be missing half.
 */
export function AccountView() {
  const { token, user, isLoading, clear, sessionOrigin } = useAuth();

  const designs = useQuery({
    queryKey: ["okh-list", "account"],
    queryFn: () => fetchOkhList({ page_size: 100 }),
    enabled: Boolean(token),
  });
  const facilities = useQuery({
    queryKey: ["okw-search", "account"],
    queryFn: () => searchOkw({ page_size: 100 }),
    enabled: Boolean(token),
  });

  if (!token) {
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

  const unsharedDesigns = (designs.data?.items ?? []).filter(
    (d) => d.visibility === "private",
  );
  const unsharedFacilities = (facilities.data?.results ?? []).filter(
    (f) => f.visibility === "private",
  );
  const anyDesigns = (designs.data?.items ?? []).length > 0;
  const anyFacilities = (facilities.data?.results ?? []).length > 0;

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
            {sessionOrigin === "minted"
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

        <UnsharedSection
          id="designs"
          title="Designs only you can see"
          browseHref="/okh"
          loading={designs.isPending}
          rows={unsharedDesigns.map((d) => ({
            id: String(d.id),
            label: d.title ?? String(d.id),
            href: `/okh/${d.id}`,
          }))}
          empty={{
            madeNothing: anyDesigns === false,
            nothing: "You have not created a design yet.",
            allShared: "Every design you can see is shared.",
          }}
        />

        <UnsharedSection
          id="facilities"
          title="Facilities only you can see"
          browseHref="/facilities"
          loading={facilities.isPending}
          rows={unsharedFacilities.map((f) => ({
            id: String(f.id),
            label: f.name ?? String(f.id),
            href: `/facilities/${f.id}`,
          }))}
          empty={{
            madeNothing: anyFacilities === false,
            nothing: "You have not created a facility yet.",
            allShared: "Every facility you can see is shared.",
          }}
        />
      </div>
    </>
  );
}

function UnsharedSection({
  id,
  title,
  browseHref,
  loading,
  rows,
  empty,
}: {
  id: string;
  title: string;
  browseHref: string;
  loading: boolean;
  rows: { id: string; label: string; href: string }[];
  /** The two silences travel together, and they mean opposite things. */
  empty: { madeNothing: boolean; nothing: string; allShared: string };
}) {
  return (
    <section className={PANEL} aria-labelledby={`unshared-${id}`}>
      <h2 id={`unshared-${id}`} className={SECTION_TITLE}>
        {title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        New records start private. Open one to share it.
      </p>

      {loading ? (
        <div className="py-6">
          <LoadingSpinner />
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">
          {empty.madeNothing ? empty.nothing : empty.allShared}{" "}
          <Link href={browseHref} className="underline">
            Browse
          </Link>
        </p>
      ) : (
        <ul className="mt-3 space-y-1">
          {rows.map((row) => (
            <li key={row.id} className="flex items-center gap-2 text-sm">
              <EyeOff aria-hidden="true" className="h-4 w-4 text-text-faint" />
              <Link href={row.href} className="underline">
                {row.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
