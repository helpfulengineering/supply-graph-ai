import { Badge } from "../../components/ui/Badge";
import type { VisibilityLevel } from "../../api/ohm/okh";

const BADGES: Record<
  VisibilityLevel,
  { label: string; variant: "yellow" | "blue" | "default" | "green" }
> = {
  private: { label: "Private", variant: "yellow" },
  members: { label: "Members", variant: "blue" },
  followers: { label: "Followers", variant: "default" },
  public: { label: "Public", variant: "green" },
};

/** Who a record is shared with, on list cards and search results (#576). */
export function VisibilityBadge({ level }: { level?: VisibilityLevel }) {
  if (!level) return null;
  const { label, variant } = BADGES[level];
  return <Badge variant={variant}>{label}</Badge>;
}
