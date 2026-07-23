import { describe, expect, it } from "vitest";
import { deleteConfirmMessage } from "./deleteConfirmMessage";

describe("deleteConfirmMessage", () => {
  it("is a simple confirm when private or unknown", () => {
    expect(deleteConfirmMessage("Lab", "private")).toBe('Delete “Lab”?');
    expect(deleteConfirmMessage("Lab", undefined)).toBe('Delete “Lab”?');
  });

  it("warns when visibility is shared", () => {
    expect(deleteConfirmMessage("Lab", "followers")).toMatch(/shared with peers/i);
    expect(deleteConfirmMessage("Lab", "public")).toMatch(/peers may keep a copy/i);
  });
});
