/**
 * Whether a component is claimed, computed here rather than trusted.
 *
 * The server's claim has a 48h TTL that it checks LAZILY, on read
 * (`ComponentState.is_claimed`). So a payload fetched two hours ago can say a
 * component is claimed when the claim has since lapsed, and a UI that renders
 * `claimed_by` as truth will show a reservation nobody holds — and hide the
 * claim control on a part that is free.
 *
 * `now` is a parameter with no default rather than a call to Date.now() inside,
 * so this is testable against a fixed clock and the caller decides what "now"
 * means.
 */

/** Matches _CLAIM_TTL in src/core/models/asset.py. */
export const CLAIM_TTL_MS = 48 * 60 * 60 * 1000;

export interface ClaimBearing {
  claimed_by?: string | null;
  claimed_at?: string | null;
}

export interface ClaimState {
  claimed: boolean;
  claimedBy: string | null;
  /** Milliseconds until the claim lapses; 0 when not claimed. */
  remainingMs: number;
  /** One line for the row, or null when the component is free. */
  label: string | null;
}

const FREE: ClaimState = {
  claimed: false,
  claimedBy: null,
  remainingMs: 0,
  label: null,
};

export function claimState(item: ClaimBearing, now: number): ClaimState {
  if (!item.claimed_by || !item.claimed_at) return FREE;
  const claimedAt = Date.parse(item.claimed_at);
  if (Number.isNaN(claimedAt)) return FREE;
  const remainingMs = claimedAt + CLAIM_TTL_MS - now;
  if (remainingMs <= 0) return FREE;
  return {
    claimed: true,
    claimedBy: item.claimed_by,
    remainingMs,
    label: `Claimed by ${item.claimed_by} — ${formatRemaining(remainingMs)} left`,
  };
}

/**
 * Coarse by design: hours until the last one, then minutes.
 *
 * A claim is a soft reservation measured in shifts, and "41h" is the number a
 * coordinator acts on. Seconds would imply a precision the lazy expiry does not
 * have.
 */
export function formatRemaining(ms: number): string {
  const minutes = Math.max(0, Math.round(ms / 60_000));
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h`;
}
