/**
 * How the map frames a set of spaces — the part that is arithmetic rather than
 * Leaflet, so it can be asserted without a container to measure.
 */

export interface LatLon {
  lat: number;
  lon: number;
}

/** [[southLat, westLon], [northLat, eastLon]] — Leaflet's corner order. */
export type Bounds = [[number, number], [number, number]];

const TILE_SIZE = 256;

/**
 * Zoom at which one copy of the world spans the narrower side of a container
 * this size — the floor below which the map stops being a map and becomes a
 * small picture of a map in a grey box.
 *
 * The narrower side, not the wider one. A dashboard panel is 1215x438: measure
 * it by its width and the floor lands at 3, which forbids ever framing the
 * whole world on the one surface whose entire job is to show it. Measure it by
 * its height and the floor is 1, the world still fits at 2, and only genuinely
 * cramped containers — a phone, where fitting a worldwide network lands at
 * zoom 0 — are pushed off the full extent.
 */
export function fillZoom(width: number, height: number): number {
  return Math.max(0, Math.ceil(Math.log2(Math.min(width, height) / TILE_SIZE)));
}

/**
 * Bounds of the busiest neighbourhood: the `cell`-degree square holding the
 * most spaces, widened to its eight neighbours and drawn tight around the
 * spaces actually in there.
 *
 * The full extent is the right frame when it fits. When it does not, the
 * fallback has to answer "where is the network", and a per-axis trim of the
 * outliers does not: this network is bimodal — the Americas and Europe — so
 * the middle 80% of longitudes centres on the Indian Ocean, which is where
 * every measurement of the phone layout landed. Density has no such failure
 * mode; the busiest square is a place.
 *
 * 10° is the coarsest cell that still resolves a region rather than a
 * hemisphere: against the live network it frames Western Europe and 53% of
 * the spaces, with the rest one pinch out.
 */
export function denseBounds(points: LatLon[], cell = 10): Bounds {
  const key = (p: LatLon) => `${Math.floor(p.lat / cell)}:${Math.floor(p.lon / cell)}`;
  const counts = new Map<string, number>();
  for (const p of points) counts.set(key(p), (counts.get(key(p)) ?? 0) + 1);

  let busiest = "";
  let most = -1;
  for (const [k, n] of counts) {
    if (n > most) {
      most = n;
      busiest = k;
    }
  }
  const [row, col] = busiest.split(":").map(Number) as [number, number];

  const near = points.filter(
    (p) =>
      Math.abs(Math.floor(p.lat / cell) - row) <= 1 &&
      Math.abs(Math.floor(p.lon / cell) - col) <= 1,
  );
  const lats = near.map((p) => p.lat);
  const lons = near.map((p) => p.lon);
  return [
    [Math.min(...lats), Math.min(...lons)],
    [Math.max(...lats), Math.max(...lons)],
  ];
}

/**
 * Inset for the initial fit. A flat 30px is a comfortable margin on a desktop
 * panel and a tenth of a phone screen, so it scales with the smaller side.
 */
export function fitPadding(width: number, height: number): number {
  return Math.round(Math.min(30, Math.min(width, height) * 0.06));
}
