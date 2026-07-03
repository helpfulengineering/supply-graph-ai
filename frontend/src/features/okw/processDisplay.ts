/**
 * Humanize an OKW manufacturing-process value for display (pure, unit-tested).
 *
 * The synthetic corpus stores processes inconsistently — Wikipedia URIs
 * (`https://en.wikipedia.org/wiki/Laser_cutter`) alongside plain names
 * (`Laser Cutting`). This yields a consistent readable label regardless. The
 * underlying data normalization is tracked separately (issue #207).
 */
export function humanizeProcess(value: string): string {
  if (/^https?:\/\//i.test(value)) {
    const tail = value.split("/").pop() || value;
    return tail
      .replace(/[_-]+/g, " ")
      .trim()
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }
  return value;
}
