"use client";

import { cn } from "@/lib/utils";
import { useId, useState, type FormEvent } from "react";
import { PANEL } from "../../components/ui/surface";
import { CAPTION } from "../../components/ui/typography";
import { SectionHeading } from "../../components/ui/SectionHeading";
import { FIELD, HINT, LABEL } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { adminStats, operatorToken } from "../../lib/site/stack";
import { useSiteQuery } from "../../lib/site/useSiteQuery";

interface OperatorPanelProps {
  isOperator: boolean;
  /** Resolves to a message on refusal, null once the token is held. */
  unlock: (token: string) => Promise<string | null>;
  lock: () => void;
  /**
   * Bumped when something elsewhere changed the event count — a purge in the
   * activity feed. The total below is the same number that feed is showing, so
   * leaving it stale means the page states two counts at once.
   */
  eventsChanged: number;
}

/**
 * The operator door: hold the token, and the panels beside this one swap their
 * masked reads for unmasked ones.
 *
 * It is a SEPARATE ACT FROM SIGNING IN, and reads like one. The gate takes a
 * name and an email nobody verifies; this takes a secret the server checks.
 * Presenting them as one control would suggest the first earns the second —
 * which is exactly the confusion `is_admin` invites, and the reason isOperator
 * no longer answers from it. Unlocking needs no visitor record at all: an
 * operator arriving on a fresh device can go straight to the token.
 *
 * The token is verified before it is stored and never rendered back, so the
 * only place it exists is this tab's sessionStorage.
 */
export function OperatorPanel({
  isOperator,
  unlock,
  lock,
  eventsChanged,
}: OperatorPanelProps) {
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const fieldId = useId();

  const stats = useSiteQuery(
    isOperator ? () => adminStats(operatorToken()) : null,
    [isOperator, eventsChanged],
  );

  async function onSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setPending(true);
    const failure = await unlock(token);
    setPending(false);
    setError(failure);
    // Cleared either way: accepted, it lives in sessionStorage and not in a
    // form field; rejected, retyping is cheaper than leaving a bad secret in
    // the DOM for a screenshot to catch.
    if (!failure) setToken("");
  }

  return (
    <section className={PANEL} aria-labelledby="ops-administration">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {/*
          "Operator access", not "Operator": the panel below is Operator
          Tools, and two headings reading "Operator" on one page would make
          the reader work out which is the door and which is the room.

          The badge sits outside the heading rather than inside its permalink:
          wrapped, "verified"/"locked" would join the link's accessible name
          and the heading would announce as a different destination depending
          on whether the reader happened to be signed in.
        */}
        <div className="flex items-center gap-2">
          <SectionHeading id="ops-administration" role="card">
            Operator access
          </SectionHeading>
          <Badge variant={isOperator ? "green" : "default"}>
            {isOperator ? "verified" : "locked"}
          </Badge>
        </div>
        {isOperator && (
          <Button type="button" variant="outline" size="lg" onClick={lock}>
            Lock
          </Button>
        )}
      </div>

      <p className={cn("mt-1", CAPTION)}>
        Unmasked visitor and telemetry reads require the operator token,
        verified server-side and held in this tab only. Site-layer operator
        status is not OHM admin.
      </p>

      {isOperator ? (
        <p className="mt-3 text-sm text-foreground">
          {stats.error ? (
            <span className="text-destructive" role="alert">
              {stats.error}
            </span>
          ) : stats.data === null ? (
            <span className="text-muted-foreground">Counting events…</span>
          ) : (
            <>
              <span className="font-mono">{stats.data.toLocaleString()}</span>{" "}
              <span className="text-muted-foreground">
                telemetry {stats.data === 1 ? "event" : "events"} recorded
              </span>
            </>
          )}
        </p>
      ) : (
        <form onSubmit={onSubmit} className="mt-3 space-y-2">
          <label htmlFor={fieldId} className={LABEL}>
            Operator token
          </label>
          <input
            id={fieldId}
            type="password"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            className={FIELD}
            aria-describedby={`${fieldId}-hint`}
            aria-invalid={error ? true : undefined}
          />
          <p id={`${fieldId}-hint`} className={HINT}>
            Set in the Supabase SQL editor — see supabase/schema.sql. Cleared
            when this tab closes.
          </p>
          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" size="lg" disabled={pending}>
            {pending ? "Checking…" : "Unlock"}
          </Button>
        </form>
      )}
    </section>
  );
}
