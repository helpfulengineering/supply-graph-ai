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

export function Badge({ children, variant = "default", className = "" }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${variantClasses[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
