/**
 * Making a decorative colour safe to read.
 *
 * The theme picker draws each world's name in that world's own accent, which
 * is the preview — but an accent is chosen to sit BEHIND text, not to be text.
 * The first correction was a fixed blend, 80% accent toward the foreground,
 * taken from the --color-primary-ink note. A fixed blend is not a contrast
 * guarantee: 80% of a pale accent is still pale, so in light mode Mono's grey
 * and Bubblegum's pink stayed under AA and their names were the two nobody
 * could read.
 *
 * A ratio is the thing that has to hold, so a ratio is what this solves for:
 * blend toward the foreground until the text clears AA against the surface it
 * is actually on, and stop there. Worlds whose accent is already legible keep
 * it undiluted; only the ones that need help lose saturation, and only as much
 * as they need.
 */

export interface Rgb {
  r: number;
  g: number;
  b: number;
}

/** WCAG 1.4.3 Contrast (Minimum), AA, for normal-size text. */
export const AA_NORMAL = 4.5;

/** Parse the `rgb(r, g, b)` / `rgba(...)` a computed style hands back. */
export function parseRgb(value: string): Rgb | null {
  const m = value.match(/-?[\d.]+/g);
  if (!m || m.length < 3) return null;
  const [r, g, b] = m.map(Number) as [number, number, number];
  return { r, g, b };
}

export function formatRgb(c: Rgb): string {
  return `rgb(${Math.round(c.r)}, ${Math.round(c.g)}, ${Math.round(c.b)})`;
}

/** `share` of `a`, the rest `b` — the sRGB blend color-mix would give. */
export function mix(a: Rgb, b: Rgb, share: number): Rgb {
  return {
    r: a.r * share + b.r * (1 - share),
    g: a.g * share + b.g * (1 - share),
    b: a.b * share + b.b * (1 - share),
  };
}

export function relativeLuminance({ r, g, b }: Rgb): number {
  const channel = (v: number) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return (
    0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
  );
}

export function contrastRatio(a: Rgb, b: Rgb): number {
  const la = relativeLuminance(a);
  const lb = relativeLuminance(b);
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

/**
 * The most accent that still reads.
 *
 * Walks the blend from pure accent toward the body text colour in 5% steps and
 * returns the first that clears `target` against `surface`. The foreground is
 * the terminus because it is the one colour already guaranteed to pass there —
 * so the search cannot fail, and a world whose accent is hopeless as ink
 * degrades to plain body text rather than to something still unreadable.
 */
export function inkFor(
  accent: Rgb,
  text: Rgb,
  surface: Rgb,
  target: number = AA_NORMAL,
): Rgb {
  for (let share = 1; share > 0; share -= 0.05) {
    const candidate = mix(accent, text, share);
    if (contrastRatio(candidate, surface) >= target) return candidate;
  }
  return text;
}
