import { describe, it, expect } from "vitest";
import { isTypingTarget, CHORD_ROUTES, SHORTCUTS } from "./shortcuts";
import { ALL_GROUPS } from "./nav";

/**
 * Routes a chord would lead somewhere useless, named rather than skipped.
 *
 * Bare /visualization is a redirect to /solutions, which has its own chord —
 * two keys for one destination is a worse contract than one.
 *
 * /operator-tools is the harder case, and the reason it is a list rather than
 * a shorter spread of nav groups. The route is conditional: it 404s unless the
 * instance runs the site layer, and the drawer hides its row to match. This
 * table is static, so a chord for it would be a key that lands on a 404 for
 * most deployments — and /help, which lists only the unconditional groups,
 * could not document it without advertising a page that is not there.
 */
const NO_CHORD = new Set(["/visualization", "/operator-tools"]);

/** The guard that keeps shortcuts out of text entry. */
function keyEvent(
  target: Partial<HTMLElement>,
  init: Partial<KeyboardEvent> = {},
) {
  return { ...init, target } as unknown as KeyboardEvent;
}

describe("isTypingTarget", () => {
  it.each(["INPUT", "TEXTAREA", "SELECT"])("guards %s", (tagName) => {
    expect(
      isTypingTarget(keyEvent({ tagName, isContentEditable: false })),
    ).toBe(true);
  });

  it("guards contenteditable, which the JSON and markdown editors use", () => {
    expect(
      isTypingTarget(keyEvent({ tagName: "DIV", isContentEditable: true })),
    ).toBe(true);
  });

  it("guards modifier combinations that belong to the browser or OS", () => {
    const div = { tagName: "DIV", isContentEditable: false };
    expect(isTypingTarget(keyEvent(div, { metaKey: true }))).toBe(true);
    expect(isTypingTarget(keyEvent(div, { ctrlKey: true }))).toBe(true);
    expect(isTypingTarget(keyEvent(div, { altKey: true }))).toBe(true);
  });

  it("allows a plain key on a non-editable element", () => {
    expect(
      isTypingTarget(keyEvent({ tagName: "DIV", isContentEditable: false })),
    ).toBe(false);
  });
});

describe("the documented contract", () => {
  it("binds a chord for every route in the sitemap", () => {
    // The gap this closes: the Create group and Reference had menu entries and
    // no keys, so the keyboard contract covered seven of twelve destinations
    // and nothing said so. Read from the nav rather than restated, so adding a
    // route fails here until it has a chord.
    //
    // ALL_GROUPS rather than NAV_GROUPS + ACCOUNT_GROUP: the narrower spread
    // exempted the Operator and Results rows by construction, so two mounted
    // routes sat outside the keyboard contract and no test could notice. The
    // exemption is now a named list instead of a consequence of which arrays
    // this line happened to read.
    const bound = new Set(Object.values(CHORD_ROUTES));
    const unbound = ALL_GROUPS.flatMap((group) => group.entries)
      .filter((entry) => !bound.has(entry.href) && !NO_CHORD.has(entry.href))
      .map((entry) => `${entry.name} (${entry.href})`);

    expect(
      unbound,
      `menu routes with no keyboard chord (add one to CHORD_ROUTES):\n${unbound.join("\n")}`,
    ).toEqual([]);
  });

  it("binds each key once", () => {
    const keys = Object.keys(CHORD_ROUTES);
    expect(new Set(keys).size).toBe(keys.length);
  });

  it("documents every chord it binds", () => {
    for (const key of Object.keys(CHORD_ROUTES)) {
      expect(
        SHORTCUTS.some((s) => s.keys.length === 2 && s.keys[1] === key),
        `chord g+${key} is listed in SHORTCUTS`,
      ).toBe(true);
    }
  });

  it("routes to in-app paths only", () => {
    for (const href of Object.values(CHORD_ROUTES)) {
      expect(href.startsWith("/")).toBe(true);
    }
  });
});
