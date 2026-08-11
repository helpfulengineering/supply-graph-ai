"use client";

import { cn } from "@/lib/utils";
import { useId, useState } from "react";
import { PANEL } from "../../components/ui/surface";
import {
  BODY_MUTED,
  CAPTION,
  CARD_TITLE,
} from "../../components/ui/typography";
import { FIELD_SM } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { instant, since } from "../../lib/site/format";
import {
  adminDeleteVisitor,
  adminUpdateVisitor,
  adminVisitors,
  operatorToken,
  visitorsMasked,
} from "../../lib/site/stack";
import { useSiteQuery } from "../../lib/site/useSiteQuery";
import type { DirectoryEntry } from "../../lib/site/rows";

interface VisitorDirectoryProps {
  /** The signed-in visitor's claim, or null. Drives the self-service read. */
  email: string | null;
  isOperator: boolean;
  /** A row this visitor owns changed, so their own panel is now stale. */
  onVisitorChanged: () => void;
}

/**
 * Who has visited this site — masked for a signed-in visitor, unmasked and
 * editable for an operator.
 *
 * ONE COMPONENT, TWO TIERS, and the tier is carried by the data rather than by
 * this component's props. `masked` comes back from the mapper that read the
 * row, so the controls below are gated on the shape of what was actually
 * returned, not on a boolean this component was handed. If the operator read
 * fails and the masked read is what rendered, the edit buttons cannot appear —
 * they are keyed to rows that, by construction, do not carry a real address to
 * edit.
 *
 * Rows are capped by the RPCs themselves (200 masked, 100 operator), so this
 * is a recent-visitors list and says so, rather than paginating a surface
 * whose backing function will not paginate.
 */
export function VisitorDirectory({
  email,
  isOperator,
  onVisitorChanged,
}: VisitorDirectoryProps) {
  const headingId = useId();
  const directory = useSiteQuery(
    isOperator
      ? () => adminVisitors(operatorToken())
      : email
        ? () => visitorsMasked(email)
        : null,
    [isOperator, email],
  );

  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [failure, setFailure] = useState<string | null>(null);

  async function mutate(
    run: () => Promise<{ ok: boolean; error?: string }>,
  ): Promise<void> {
    const result = await run();
    setFailure(result.ok ? null : (result.error ?? "The change was refused."));
    if (result.ok) {
      directory.reload();
      onVisitorChanged();
    }
  }

  function startEdit(entry: DirectoryEntry): void {
    setEditing(entry.email);
    setDraft(entry.name);
  }

  const rows = directory.data ?? [];
  /** Neither tier: no read was attempted, so an empty list means nothing. */
  const locked = !isOperator && !email;

  return (
    <section className={PANEL} aria-labelledby={headingId}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className={CARD_TITLE}>
          Visitors
        </h2>
        <Badge variant={isOperator ? "green" : "default"}>
          {isOperator ? "unmasked" : "masked"}
        </Badge>
      </div>
      <p className={cn("mt-1", CAPTION)}>
        {isOperator
          ? "The 100 most recent visitors, with real addresses. Renaming, the admin marker, and deletion all go through the operator token."
          : "The 200 most recent visitors. Addresses are masked and user agents are never returned — only your own record is yours to read in full."}
      </p>

      {directory.loading && rows.length === 0 && (
        <p className={cn("mt-4", BODY_MUTED)} role="status">
          Loading visitors…
        </p>
      )}
      {directory.error && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {directory.error}
        </p>
      )}
      {failure && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {failure}
        </p>
      )}

      {!directory.loading && !directory.error && rows.length === 0 && (
        // "None recorded" and "none you may read" are different facts, and the
        // panel used to state the first when the second was true: with no
        // visitor and no token nothing is fetched at all, so an empty list is
        // the absence of a question, not an answer. Saying so is the only
        // honest empty state — and it is what makes this panel worth
        // rendering to a reader who is in neither tier.
        <p className={cn("mt-4", BODY_MUTED)}>
          {locked
            ? "Sign in at the gate to see the masked list, or unlock with the operator token for the full one."
            : "No visitors recorded yet."}
        </p>
      )}

      {rows.length > 0 && (
        <ul className="mt-4 divide-y divide-border">
          {rows.map((entry) => (
            <li
              key={entry.email}
              className="flex flex-wrap items-center justify-between gap-2 py-3"
            >
              <div className="min-w-0">
                {editing === entry.email ? (
                  <input
                    value={draft}
                    maxLength={120}
                    aria-label={`Name for ${entry.email}`}
                    onChange={(e) => setDraft(e.target.value)}
                    className={FIELD_SM}
                  />
                ) : (
                  <p className="font-medium text-foreground">
                    {entry.name}{" "}
                    {entry.isAdmin && (
                      <Badge variant="indigo" className="ml-1 align-middle">
                        admin marker
                      </Badge>
                    )}
                  </p>
                )}
                <p className={cn("truncate font-mono", CAPTION)}>
                  {entry.email}
                </p>
                <p className={CAPTION}>
                  last seen{" "}
                  <time title={instant(entry.lastSeen)}>
                    {since(entry.lastSeen)}
                  </time>
                  {entry.firstSeen && (
                    <>
                      {" · first seen "}
                      <time title={instant(entry.firstSeen)}>
                        {since(entry.firstSeen)}
                      </time>
                    </>
                  )}
                </p>
              </div>

              {!entry.masked && (
                <div className="flex flex-wrap gap-2">
                  {editing === entry.email ? (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        disabled={!draft.trim()}
                        onClick={() =>
                          void mutate(async () => {
                            const r = await adminUpdateVisitor(
                              operatorToken(),
                              entry.email,
                              {
                                name: draft.trim(),
                              },
                            );
                            if (r.ok) setEditing(null);
                            return r;
                          })
                        }
                      >
                        Save
                      </Button>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => setEditing(null)}
                      >
                        Cancel
                      </Button>
                    </>
                  ) : (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => startEdit(entry)}
                    >
                      Rename
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      void mutate(() =>
                        adminUpdateVisitor(operatorToken(), entry.email, {
                          isAdmin: !entry.isAdmin,
                        }),
                      )
                    }
                  >
                    {entry.isAdmin ? "Clear admin marker" : "Set admin marker"}
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={() => {
                      if (
                        window.confirm(
                          `Delete ${entry.email} and every telemetry event attributed to it? This cannot be undone.`,
                        )
                      ) {
                        void mutate(() =>
                          adminDeleteVisitor(operatorToken(), entry.email),
                        );
                      }
                    }}
                  >
                    Delete
                  </Button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
