import { VisibilityControl } from "../okh/VisibilityControl";
import { DisclosureControl } from "./DisclosureControl";

/**
 * Single Sharing composition for OKW facilities: visibility (whether / to whom)
 * then disclosure (how much), with peer preview inside DisclosureControl.
 */
export function SharingPanel({ id }: { id: string }) {
  return (
    <section
      aria-labelledby="okw-sharing-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
    >
      <h2
        id="okw-sharing-heading"
        className="mb-1 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
      >
        Sharing
      </h2>
      <p className="mb-5 text-xs text-slate-500 dark:text-slate-400">
        Control what federation peers can receive. Visibility chooses whether (and to whom)
        this facility is exported; disclosure chooses which field groups each audience gets.
      </p>
      <div className="space-y-6">
        <VisibilityControl
          kind="okw"
          id={id}
          variant="plain"
          hint="private = local only. followers / public export the matching disclosure profile."
        />
        <div className="border-t border-slate-200 pt-5 dark:border-slate-700">
          <DisclosureControl id={id} variant="plain" />
        </div>
      </div>
    </section>
  );
}
