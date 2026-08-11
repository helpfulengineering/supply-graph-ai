type Variant = "default" | "green" | "yellow" | "red" | "blue" | "indigo";

// Variants name a hue rather than a meaning (callers pick "green" for healthy,
// "yellow" for degraded), so the mapping is where hue becomes token. Ink is the
// blended `-ink` variant, not the raw status colour: a mid-lightness hue on a
// 10% wash of itself lands under AA.
const variantClasses: Record<Variant, string> = {
  default: "bg-muted text-muted-foreground",
  green: "bg-success/10 text-success-ink",
  yellow: "bg-warning/10 text-warning-ink",
  red: "bg-destructive/10 text-destructive-ink",
  blue: "bg-info/10 text-info-ink",
  indigo: "bg-accent text-primary-ink",
};

interface Props {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}

/**
 * One size, one corner.
 *
 * `rounded-lg`, which is the world's own `--ttm-radius` — the same corner the
 * panels are cut with. A pill at 9999px was a shape from a different system
 * sitting inside a card the theme had already given an opinion about, and in
 * the squarer worlds (Terminal, Blueprint) the mismatch is the first thing you
 * see on the card.
 *
 * `whitespace-nowrap shrink-0` is the size half. A badge is a label, not a
 * paragraph: beside a long facility name the source badge was being squeezed
 * until "Maps of Making" broke over two lines, so the same badge was one
 * height on one card and two on the next, down a column where they are meant
 * to line up.
 */
export function Badge({ children, variant = "default", className = "" }: Props) {
  return (
    <span
      className={`inline-flex shrink-0 items-center whitespace-nowrap rounded-lg px-2 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
