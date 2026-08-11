import { describe, it, expect } from "vitest";
import { isTypingTarget, CHORD_ROUTES, SHORTCUTS } from "./shortcuts";

/** The guard that keeps shortcuts out of text entry. */
function keyEvent(target: Partial<HTMLElement>, init: Partial<KeyboardEvent> = {}) {
  return { ...init, target } as unknown as KeyboardEvent;
}

describe("isTypingTarget", () => {
  it.each(["INPUT", "TEXTAREA", "SELECT"])("guards %s", (tagName) => {
    expect(isTypingTarget(keyEvent({ tagName, isContentEditable: false }))).toBe(true);
  });

  it("guards contenteditable, which the JSON and markdown editors use", () => {
    expect(isTypingTarget(keyEvent({ tagName: "DIV", isContentEditable: true }))).toBe(
      true,
    );
  });

  it("guards modifier combinations that belong to the browser or OS", () => {
    const div = { tagName: "DIV", isContentEditable: false };
    expect(isTypingTarget(keyEvent(div, { metaKey: true }))).toBe(true);
    expect(isTypingTarget(keyEvent(div, { ctrlKey: true }))).toBe(true);
    expect(isTypingTarget(keyEvent(div, { altKey: true }))).toBe(true);
  });

  it("allows a plain key on a non-editable element", () => {
    expect(isTypingTarget(keyEvent({ tagName: "DIV", isContentEditable: false }))).toBe(
      false,
    );
  });
});

describe("the documented contract", () => {
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
