import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { SegmentedControl } from "./SegmentedControl";

const OPTIONS = [
  { value: "minimal" as const, label: "Minimal" },
  { value: "standard" as const, label: "Standard" },
  { value: "strict" as const, label: "Strict" },
];

function Harness({ onChange }: { onChange?: (v: string) => void }) {
  const [value, setValue] = useState<"minimal" | "standard" | "strict">(
    "standard",
  );
  return (
    <SegmentedControl
      label="System mode"
      value={value}
      options={OPTIONS}
      onChange={(v) => {
        setValue(v);
        onChange?.(v);
      }}
    />
  );
}

const radios = () => screen.getAllByRole("radio");

describe("SegmentedControl", () => {
  it("exposes the group and its selection to assistive technology", () => {
    render(<Harness />);
    expect(screen.getByRole("radiogroup", { name: "System mode" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Standard" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Minimal" })).not.toBeChecked();
  });

  it("is a single tab stop, on the selected segment", async () => {
    // The roving tabindex. Three segments each carrying tabIndex=0 would make
    // one control cost three Tab presses to move past, which is what the
    // hand-rolled versions did.
    render(<Harness />);
    expect(radios().map((r) => r.getAttribute("tabindex"))).toEqual([
      "-1",
      "0",
      "-1",
    ]);

    await userEvent.tab();
    expect(screen.getByRole("radio", { name: "Standard" })).toHaveFocus();
    await userEvent.tab();
    expect(radios().some((r) => r === document.activeElement)).toBe(false);
  });

  it("moves selection and focus together with the arrow keys", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await userEvent.tab();

    await userEvent.keyboard("{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("strict");
    expect(screen.getByRole("radio", { name: "Strict" })).toHaveFocus();
    expect(screen.getByRole("radio", { name: "Strict" })).toBeChecked();

    await userEvent.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenLastCalledWith("standard");
    expect(screen.getByRole("radio", { name: "Standard" })).toHaveFocus();
  });

  it("wraps at both ends so the group has no dead end", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await userEvent.tab();

    await userEvent.keyboard("{ArrowRight}{ArrowRight}");
    expect(onChange).toHaveBeenLastCalledWith("minimal");

    await userEvent.keyboard("{ArrowLeft}");
    expect(onChange).toHaveBeenLastCalledWith("strict");
  });

  it("supports Home and End", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await userEvent.tab();

    await userEvent.keyboard("{Home}");
    expect(onChange).toHaveBeenLastCalledWith("minimal");
    await userEvent.keyboard("{End}");
    expect(onChange).toHaveBeenLastCalledWith("strict");
  });

  it("treats Down/Up as Right/Left, per the radio group pattern", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await userEvent.tab();

    await userEvent.keyboard("{ArrowDown}");
    expect(onChange).toHaveBeenLastCalledWith("strict");
    await userEvent.keyboard("{ArrowUp}");
    expect(onChange).toHaveBeenLastCalledWith("standard");
  });

  it("still selects on click", async () => {
    const onChange = vi.fn();
    render(<Harness onChange={onChange} />);
    await userEvent.click(screen.getByRole("radio", { name: "Minimal" }));
    expect(onChange).toHaveBeenCalledWith("minimal");
    expect(screen.getByRole("radio", { name: "Minimal" })).toBeChecked();
  });

  it("puts the tab stop on the first segment when nothing is selected", () => {
    // A group can render before its value exists (a URL-driven filter on first
    // paint). With no segment selected, every tabIndex would be -1 and the
    // control would drop out of the tab order entirely.
    render(
      <SegmentedControl
        label="View"
        value={"" as unknown as "minimal"}
        options={OPTIONS}
        onChange={() => {}}
      />,
    );
    expect(radios().map((r) => r.getAttribute("tabindex"))).toEqual([
      "0",
      "-1",
      "-1",
    ]);
  });
});
