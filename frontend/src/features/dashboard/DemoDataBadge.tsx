"use client";

import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { demoModeEnabled } from "../../lib/demo/demoMode";

/**
 * "Demo data" indicator — shown only while demo mode is ACTIVE.
 *
 * It deliberately does not reflect server-seeded records. An operator who ran
 * `make seed-demo` has simply put data in their instance; badging every page
 * forever for that is noise, and the badge stops meaning anything. Demo mode
 * is a state the visitor turned on and can turn off, so the badge marks a
 * state, not a data provenance.
 *
 * Read after mount rather than during render: localStorage is not available on
 * the server, and reading it in render would make the first client paint
 * disagree with the markup.
 */
export function DemoDataBadge() {
  const [active, setActive] = useState(false);

  useEffect(() => setActive(demoModeEnabled()), []);

  if (!active) return null;

  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-0.5 text-xs font-medium text-warning-ink"
      title="Demo mode is on — this page is showing a bundled sample world, not this instance's data"
    >
      <FlaskConical aria-hidden="true" className="h-3.5 w-3.5" />
      Demo data
    </span>
  );
}
