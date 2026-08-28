import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { PANEL } from "./surface";

/**
 * A titled group of related controls.
 *
 * One component per concept, for a concept that had four spellings — two
 * panel-styled `<fieldset>`s in the match feature with their own border and
 * radius, and two bare ones in settings with a hand-styled `<legend>`.
 *
 * The reason it is a component and not another string constant in `surface.ts`
 * is the `min-w-0`. `<fieldset>` is the one element with
 *
 *     min-inline-size: min-content
 *
 * in the UA stylesheet — a rule that exists for historical layout reasons and
 * has no equivalent on `<div>`. It means a fieldset will not shrink below its
 * widest descendant no matter what its parent is doing, so a fieldset holding
 * a list of long names grows past the viewport and takes the page's horizontal
 * scroll with it. That was the /match bug: a 920px facilities panel in a 360px
 * window, with the header and footer ending at the screen edge and reading as
 * though the chrome were too narrow.
 *
 * An author `min-width: 0` overrides it, but only if it is actually written,
 * every time — which is exactly the kind of invisible obligation a constant
 * cannot carry and a component can. `e2e/responsive.spec.ts` measures the
 * result, so a regression here fails the gate rather than shipping.
 */
export function Fieldset({
  legend,
  legendHidden = false,
  description,
  children,
  className,
}: {
  /** The group's name. Always rendered — visually hidden if `legendHidden`. */
  legend: ReactNode;
  /** For a group whose purpose is already stated by surrounding copy. */
  legendHidden?: boolean;
  /** One line under the legend, describing what the group is for. */
  description?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <fieldset className={cn(PANEL, "min-w-0", className)}>
      <legend
        className={
          legendHidden
            ? "sr-only"
            : "px-1 text-sm font-medium text-foreground"
        }
      >
        {legend}
      </legend>
      {description && (
        <p className="mb-3 text-xs text-muted-foreground">{description}</p>
      )}
      {children}
    </fieldset>
  );
}
