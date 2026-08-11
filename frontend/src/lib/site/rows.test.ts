import { describe, expect, it } from "vitest";
import {
  toDeletedCount,
  toEventTotal,
  toMaskedActivity,
  toMaskedDirectory,
  toOperatorActivity,
  toOperatorDirectory,
  toOwnRecord,
} from "./rows";

function visitorRow(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    name: "Ada Lovelace",
    email: "ada@example.org",
    first_seen: "2026-08-01T09:00:00.000Z",
    last_seen: "2026-08-11T09:00:00.000Z",
    is_admin: false,
    ...overrides,
  };
}

function eventRow(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    ts: "2026-08-11T09:00:00.000Z",
    event: "page_view",
    page: "/match",
    session_id: "0f8e7d6c-1111-2222-3333-444455556666",
    visitor_email: "ada@example.org",
    ...overrides,
  };
}

describe("toOwnRecord", () => {
  it("reads the row out of the one-row set the RPC returns", () => {
    const record = toOwnRecord([visitorRow({ is_admin: true })]);
    expect(record).toEqual({
      name: "Ada Lovelace",
      email: "ada@example.org",
      firstSeen: "2026-08-01T09:00:00.000Z",
      lastSeen: "2026-08-11T09:00:00.000Z",
      isAdmin: true,
    });
  });

  it("is null for an unknown email, which comes back as an empty set", () => {
    expect(toOwnRecord([])).toBeNull();
    expect(toOwnRecord(null)).toBeNull();
  });

  it("treats the admin marker as strictly boolean", () => {
    // The column is the display marker, never access — a truthy string must
    // not be read as "yes".
    expect(toOwnRecord([visitorRow({ is_admin: "true" })])?.isAdmin).toBe(false);
  });
});

describe("directory mappers", () => {
  it("marks the masked read as masked and withholds first_seen", () => {
    const [entry] = toMaskedDirectory([
      { name: "Ada Lovelace", email_masked: "a***@e***", last_seen: "2026-08-11T09:00:00.000Z", is_admin: false },
    ]);
    expect(entry).toEqual({
      name: "Ada Lovelace",
      email: "a***@e***",
      masked: true,
      firstSeen: null,
      lastSeen: "2026-08-11T09:00:00.000Z",
      isAdmin: false,
    });
  });

  it("marks the operator read as unmasked and carries the real address", () => {
    const [entry] = toOperatorDirectory([visitorRow()]);
    expect(entry.masked).toBe(false);
    expect(entry.email).toBe("ada@example.org");
    expect(entry.firstSeen).toBe("2026-08-01T09:00:00.000Z");
  });

  it("survives a response that is not a list", () => {
    expect(toMaskedDirectory(null)).toEqual([]);
    expect(toOperatorDirectory({ error: "nope" })).toEqual([]);
  });
});

describe("activity mappers", () => {
  it("withholds the session id on the masked read", () => {
    const [entry] = toMaskedActivity([
      { ts: "2026-08-11T09:00:00.000Z", event: "page_view", page: "/match", visitor_masked: "a***@e***" },
    ]);
    expect(entry.sessionId).toBeNull();
    expect(entry.masked).toBe(true);
    expect(entry.visitor).toBe("a***@e***");
  });

  it("carries the session and real address on the operator read", () => {
    const [entry] = toOperatorActivity([eventRow()]);
    expect(entry.masked).toBe(false);
    expect(entry.sessionId).toBe("0f8e7d6c-1111-2222-3333-444455556666");
    expect(entry.visitor).toBe("ada@example.org");
  });

  it("renders an unattributed event rather than dropping it", () => {
    const [entry] = toOperatorActivity([eventRow({ visitor_email: null, page: null })]);
    expect(entry.event).toBe("page_view");
    expect(entry.visitor).toBe("");
    expect(entry.page).toBeNull();
  });
});

describe("count mappers", () => {
  it("reads a bigint returned as a string", () => {
    // Postgres bigints arrive over PostgREST as strings once they are large.
    expect(toEventTotal([{ total_events: "128000" }])).toBe(128_000);
    expect(toDeletedCount("42")).toBe(42);
  });

  it("reads a plain number", () => {
    expect(toEventTotal([{ total_events: 7 }])).toBe(7);
    expect(toDeletedCount(0)).toBe(0);
  });

  it("falls back to zero rather than NaN", () => {
    expect(toEventTotal([])).toBe(0);
    expect(toEventTotal(null)).toBe(0);
    expect(toDeletedCount(undefined)).toBe(0);
    expect(toDeletedCount("not a number")).toBe(0);
  });
});
