/**
 * The OHM mark: a hex nut that is also a network.
 *
 * Two readings, both true to the product. From across the room it is a
 * hex nut — hardware, unmistakably. Up close its interior is a supply graph:
 * one design resolving into the facilities that can build it, which is the
 * thing the app actually does. The nut's outline is broken at the top, so the
 * hardware is literally open.
 *
 * Not an omega: "OHM" is an acronym for Open Hardware Manager, not the unit of
 * resistance, and a mark punning on that coincidence would advertise something
 * the product is not.
 *
 * Inline in the document, so unlike the favicon it reads the token ramp
 * directly and re-themes with every world.
 */
export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  const gradientId = "ohm-mark-pearl";
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      role="img"
      aria-label="Open Hardware Manager"
      fill="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--ttm-irid-a)" />
          <stop offset="30%" stopColor="var(--ttm-irid-b)" />
          <stop offset="60%" stopColor="var(--ttm-irid-c)" />
          <stop offset="100%" stopColor="var(--ttm-irid-e)" />
        </linearGradient>
      </defs>

      {/* Nut silhouette, opened at the top edge. Drawn as two arms from the
          gap rather than a closed polygon, so the opening is structural. */}
      <path
        d="M19.4 3.2 L27.4 8.0 V24.0 L16 29.6 L4.6 24.0 V8.0 L12.6 3.2"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Interior: the supply graph — design above, two makers below. */}
      {/* Weights tuned at 16px, not 96px: thin strokes and small nodes turned
          to mush at favicon scale, where this mark spends most of its life. */}
      <path
        d="M16 12 L10.6 21 M16 12 L21.4 21"
        stroke={`url(#${gradientId})`}
        strokeWidth="2.2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="11.4" r="3.1" fill={`url(#${gradientId})`} />
      <circle cx="10.3" cy="21.4" r="2.7" fill={`url(#${gradientId})`} />
      <circle cx="21.7" cy="21.4" r="2.7" fill={`url(#${gradientId})`} />
    </svg>
  );
}
