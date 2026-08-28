"use client";

import { useMemo, useState } from "react";
import { PageHero } from "../../components/layout/PageHero";
import { FIELD, LABEL } from "../../components/ui/field";
import { PANEL } from "../../components/ui/surface";
import { BODY_MUTED, CAPTION } from "../../components/ui/typography";
import { SectionHeading } from "../../components/ui/SectionHeading";
import { ALL_ICONS } from "../../components/icons/gallery";
import { MAPPED_PROCESS_IDS, processIcon } from "../../components/icons/processIcons";
import { humanizeProcessId } from "../network/deriveFilterOptions";
import { cn } from "@/lib/utils";

/**
 * Every glyph the app owns, and what each process draws.
 *
 * Unlisted on purpose — it is not in the sitemap and nothing links to it,
 * because it is a workbench for whoever is wiring an icon, not a page a
 * visitor has any use for. It is not access-controlled either, and should not
 * pretend to be: everything on it ships in the client bundle already.
 */
export function IconGalleryView() {
  const [query, setQuery] = useState("");

  const q = query.trim().toLowerCase();
  const glyphs = useMemo(
    () => ALL_ICONS.filter((g) => !q || g.name.includes(q)),
    [q],
  );
  const processes = useMemo(
    () =>
      MAPPED_PROCESS_IDS.filter(
        (id) => !q || id.includes(q) || humanizeProcessId(id).toLowerCase().includes(q),
      ),
    [q],
  );

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* "internal" stays text: it says what this page is — a reference for
          people building the interface — rather than naming a third section. */}
      <PageHero
        title="Icons"
        crumb={[
          { label: "glyphs", href: "#glyphs-heading" },
          { label: "processes", href: "#processes-heading" },
          { label: "internal" },
        ]}
      />

      <div className="max-w-md">
        <label htmlFor="icon-search" className={LABEL}>
          Filter
        </label>
        <input
          id="icon-search"
          type="search"
          value={query}
          placeholder="e.g. weld, cnc, laser"
          onChange={(e) => setQuery(e.target.value)}
          className={FIELD}
        />
        <p className={cn(CAPTION, "mt-1")}>
          Matches a glyph name or a process id.
        </p>
      </div>

      <section aria-labelledby="glyphs-heading" className="space-y-3">
        <SectionHeading id="glyphs-heading">
          Glyphs ({glyphs.length})
        </SectionHeading>
        <p className={BODY_MUTED}>
          Every icon checked in under <code>components/icons/noun</code>. They
          take their colour from the token layer, so this grid re-themes with
          the rest of the app.
        </p>
        <ul className="grid list-none grid-cols-3 gap-3 p-0 sm:grid-cols-5 lg:grid-cols-8">
          {glyphs.map(({ name, Icon }) => (
            <li key={name} className={cn(PANEL, "flex flex-col items-center gap-2")}>
              <Icon className="h-8 w-8 text-primary-ink" />
              <span className={cn(CAPTION, "break-all text-center")}>{name}</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="processes-heading" className="space-y-3">
        <SectionHeading id="processes-heading">
          Processes ({processes.length})
        </SectionHeading>
        <p className={BODY_MUTED}>
          Every process in the taxonomy and the glyph it draws. A row with no
          icon is a gap the coverage test would already have failed on.
        </p>
        <ul className="grid list-none grid-cols-2 gap-2 p-0 sm:grid-cols-3 lg:grid-cols-4">
          {processes.map((id) => {
            const Icon = processIcon(id);
            return (
              <li
                key={id}
                className={cn(PANEL, "flex items-center gap-2.5 py-2")}
              >
                {Icon ? (
                  <Icon className="h-5 w-5 shrink-0 text-primary-ink" />
                ) : (
                  <span className="h-5 w-5 shrink-0 rounded border border-dashed border-border" />
                )}
                <span className="min-w-0">
                  <span className="block truncate text-sm text-foreground">
                    {humanizeProcessId(id)}
                  </span>
                  <code className={cn(CAPTION, "block truncate")}>{id}</code>
                </span>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
