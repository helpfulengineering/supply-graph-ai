"use client";

import { useId, useState } from "react";
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

interface ActivityFeedProps {
  email: string | null;
  isOperator: boolean;
  /** A purge landed: the operator panel's total is now wrong. */
  onEventsChanged: () => void;
}

const DEFAULT_KEEP_DAYS = 30;

/**
 * The telemetry itself: what was tracked, on which page, by whom.
 *
 * Masked for a signed-in visitor, unmasked with session ids for an operator,
 * on the same one-component-two-tiers rule as the directory — the row's own
 * `masked` flag gates the columns and the purge control, so a fallback to the
 * self-service read cannot render an operator affordance.
 *
 * PURGE IS HERE RATHER THAN IN A SETTINGS DRAWER because retention is the
 * thing an operator actually wants after reading a feed of what they collected
 * — and a site layer whose only advertised power over its own telemetry was
 * "collect more" would be an odd thing to hand someone. It is bounded by days
 * kept rather than a "delete all" button: the useful operation is a retention
 * window, and the destructive one is a slip.
 */
export function ActivityFeed({ email, isOperator, onEventsChanged }: ActivityFeedProps) {
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

  return (
    <section className={PANEL} aria-labelledby={headingId}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={headingId} className={CARD_TITLE}>
          Activity
        </h2>
        <Badge variant={isOperator ? "green" : "default"}>
          {isOperator ? "unmasked" : "masked"}
        </Badge>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        {isOperator
          ? "The 200 most recent telemetry events, with the address and session behind each."
          : "The 200 most recent telemetry events. Addresses are masked, and sessions are not returned."}
      </p>

      {events.loading && rows.length === 0 && (
        <p className="mt-4 text-sm text-muted-foreground" role="status">
          Loading activity…
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
        <ul className={`${SCROLL_LIST} mt-4`}>
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
