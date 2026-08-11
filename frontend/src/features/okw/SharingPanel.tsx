import { VisibilityControl } from "../okh/VisibilityControl";
import { DisclosureControl } from "./DisclosureControl";
import { PANEL } from "../../components/ui/surface";
import { SECTION_LABEL } from "../../components/ui/typography";
import { cn } from "@/lib/utils";

/**
 * Single Sharing composition for OKW facilities: visibility (whether / to whom)
 * then disclosure (how much), with peer preview inside DisclosureControl.
 */
export function SharingPanel({ id }: { id: string }) {
  return (
    <section
      id="sharing"
      aria-labelledby="okw-sharing-heading"
      className={PANEL}
    >
      <h2 id="okw-sharing-heading" className={cn(SECTION_LABEL, "mb-1")}>
        Sharing
      </h2>
      <p className="mb-5 text-xs text-muted-foreground">
        Control what federation peers can receive. Visibility chooses whether
        (and to whom) this facility is exported; disclosure chooses which field
        groups each audience gets.
      </p>
      <div className="space-y-6">
        <VisibilityControl
          kind="okw"
          id={id}
          variant="plain"
          hint="private = local only. followers / public export the matching disclosure profile."
        />
        <div className="border-t border-border pt-5">
          <DisclosureControl id={id} variant="plain" />
        </div>
      </div>
    </section>
  );
}
