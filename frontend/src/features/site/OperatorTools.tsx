"use client";

import { useId, useMemo, useState } from "react";
import { PANEL, SCROLL_LIST } from "../../components/ui/surface";
import { CARD_TITLE } from "../../components/ui/typography";
import { FIELD_SM } from "../../components/ui/field";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/Badge";
import { age, instant } from "../../lib/site/format";
import {
  adminEvents,
  adminPurgeEvents,
  eventsMasked,
  operatorToken,
} from "../../lib/site/stack";
import { useSiteQuery } from "../../lib/site/useSiteQuery";
import { summarize } from "../../lib/site/summary";
import { PANEL_INSET } from "../../components/ui/surface";

interface OperatorToolsProps {
  email: string | null;
  isOperator: boolean;
  /** A purge landed: the operator panel's total is now wrong. */
  onEventsChanged: () => void;
}

const DEFAULT_KEEP_DAYS = 30;

/**
 * Operator Tools — the telemetry, read as the questions an operator opens this
 * page with rather than as the log it is stored in.
 *
 * FRAMING, AND WHY IT CHANGES THE CONTENT. A reverse-chronological feed is a
 * faithful rendering of the table and a poor answer to anything: "what is this
 * instance for", "is it working", "what should I do next" are all counting
 * questions, and a list sorted by time answers none of them. So the panel
 * leads with the answers and demotes the feed to the evidence underneath.
 *
 * The section that justifies the framing is UNMET DEMAND: designs people ran a
 * match against that came back with nothing. Every other figure here reports
 * what the instance did; that one reports what it could not do, and names the
 * gap in the facility network an operator can actually go and fill. It is also
 * the one thing page views structurally cannot show — a match that finds
 * nothing renders an ordinary page and looks like success in traffic.
 *
 * Masked for a signed-in visitor, unmasked for an operator, on the same
 * one-component-two-tiers rule as the directory: the row's own `masked` flag
 * gates the columns, the outcome figures, and the purge, so a fallback to the
 * self-service read cannot render an operator affordance.
 *
 * RETENTION IS HERE rather than in a settings drawer, because deciding how
 * long to keep this is part of reading it — and a layer whose only advertised
 * power over its own telemetry was "collect more" would be an odd thing to
 * hand someone. Bounded by days kept rather than a "delete all" button: the
 * useful operation is a retention window, and the destructive one is a slip.
 */
export function OperatorTools({ email, isOperator, onEventsChanged }: OperatorToolsProps) {
  const headingId = useId();
  const keepId = useId();
  const events = useSiteQuery(
    isOperator
      ? () => adminEvents(operatorToken())
      : email
        ? () => eventsMasked(email)
        : null,
    [isOperator, email],
  );

  const [keepDays, setKeepDays] = useState(String(DEFAULT_KEEP_DAYS));
  const [notice, setNotice] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  async function onPurge(): Promise<void> {
    // Blank is not zero, though `Number("")` is: an operator who cleared the
    // field and clicked Purge would otherwise be asked to confirm deleting
    // every event they own, having expressed no window at all.
    const entered = keepDays.trim();
    const days = Number(entered);
    if (entered === "" || !Number.isFinite(days) || days < 0) {
      setFailure("Enter a number of days to keep.");
      return;
    }
    const ok = window.confirm(
      days === 0
        ? "Delete every telemetry event? This cannot be undone."
        : `Delete telemetry events older than ${days} days? This cannot be undone.`,
    );
    if (!ok) return;

    const result = await adminPurgeEvents(operatorToken(), days);
    if (result.ok) {
      setFailure(null);
      setNotice(`Deleted ${result.data.toLocaleString()} ${result.data === 1 ? "event" : "events"}.`);
      events.reload();
      onEventsChanged();
    } else {
      setNotice(null);
      setFailure(result.error);
    }
  }

  const rows = events.data ?? [];
  const summary = useMemo(() => summarize(rows), [rows]);
  const outcomesVisible = rows.some((row) => !row.masked);

  return (
    <section className={PANEL} aria-labelledby={headingId}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className={CARD_TITLE}>
          Operator Tools
        </h2>
        <Badge variant={isOperator ? "green" : "default"}>
          {isOperator ? "unmasked" : "masked"}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {isOperator
          ? "What this instance is being used for, drawn from the 200 most recent events — with the address, session, and outcome behind each."
          : "What this instance is being used for, drawn from the 200 most recent events. Addresses are masked, and sessions and outcomes are not returned."}
      </p>

      {events.loading && rows.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground" role="status">
          Loading…
        </p>
      )}
      {events.error && (
        <p className="mt-4 text-sm text-destructive" role="alert">
          {events.error}
        </p>
      )}
      {!events.loading && !events.error && rows.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground">
          No telemetry events recorded yet.
        </p>
      )}

      {rows.length > 0 && (
        <div className={`${PANEL_INSET} mt-3`}>
          <dl className="flex flex-wrap gap-x-6 gap-y-2 text-xs">
            <div>
              <dt className="text-muted-foreground">Events</dt>
              <dd className="mt-0.5 font-mono text-foreground">
                {summary.events
                  .map((e) => `${e.label} ${e.count}`)
                  .join("  ·  ") || "—"}
              </dd>
            </div>
            {summary.pages.length > 0 && (
              <div className="min-w-0">
                <dt className="text-muted-foreground">Busiest pages</dt>
                <dd className="mt-0.5 truncate font-mono text-foreground">
                  {summary.pages.map((p) => `${p.label} ${p.count}`).join("  ·  ")}
                </dd>
              </div>
            )}
            {/*
              Outcomes need the props column, which only the operator read
              returns — so this is gated on the rows themselves, like every
              other unmasked affordance here. Rendered on masked data it would
              say "0 of 3", and that zero would mean "cannot see" while
              reading as "none failed": a number that lies is worse than one
              that is absent.
            */}
            {outcomesVisible && summary.unmetDemand.length > 0 && (
              <div className="min-w-0 basis-full">
                <dt className="text-muted-foreground">
                  Unmet demand — matched here, nothing could make it
                </dt>
                <dd className="mt-0.5 truncate font-mono text-warning-ink">
                  {summary.unmetDemand
                    .map((d) => `${d.label}${d.count > 1 ? ` ×${d.count}` : ""}`)
                    .join("  ·  ")}
                </dd>
              </div>
            )}
            {outcomesVisible && summary.matchRuns > 0 && (
              <div>
                <dt className="text-muted-foreground">Matches returning nothing</dt>
                <dd className="mt-0.5 font-mono text-foreground">
                  {summary.emptyMatchRuns} of {summary.matchRuns}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}

      {rows.length > 0 && (
        <ul className={`${SCROLL_LIST} mt-3`}>
          {rows.map((entry, i) => (
            <li
              // Events carry no id of their own, and a busy site can write two
              // in the same millisecond — the index is what actually
              // distinguishes them in an ordered, read-only list.
              key={`${entry.ts}-${i}`}
              className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 px-2 py-1.5"
            >
              <span className="font-mono text-xs text-foreground">{entry.event}</span>
              <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">
                {entry.page ?? "—"}
                {entry.visitor && <> · {entry.visitor}</>}
                {entry.sessionId && (
                  <> · <span className="font-mono">{entry.sessionId.slice(0, 8)}</span></>
                )}
              </span>
              <time className="text-xs text-muted-foreground" title={instant(entry.ts)}>
                {age(entry.ts)}
              </time>
            </li>
          ))}
        </ul>
      )}

      {isOperator && (
        <div className="mt-4 border-t border-border pt-4">
          <label htmlFor={keepId} className="text-xs font-medium text-foreground">
            Retention — delete events older than
          </label>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              id={keepId}
              type="number"
              min={0}
              max={3650}
              value={keepDays}
              onChange={(e) => setKeepDays(e.target.value)}
              className={`${FIELD_SM} w-24`}
            />
            <span className="text-xs text-muted-foreground">days</span>
            <Button type="button" variant="destructive" size="sm" onClick={() => void onPurge()}>
              Purge
            </Button>
            {notice && (
              <span className="text-xs text-success-ink" role="status">
                {notice}
              </span>
            )}
          </div>
          {failure && (
            <p className="mt-2 text-sm text-destructive" role="alert">
              {failure}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
