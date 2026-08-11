import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import "./networkMap.css";
import type { NetworkSpace } from "../../api/ohm/network";
import { SOURCE_STYLES, sourceColor } from "./networkSummary";
import { useSourceColors } from "./useSourceColors";
import { denseBounds, fillZoom, fitPadding } from "./mapFraming";
import { displayCountryName } from "../match/geoDisplay";

/**
 * `leaflet.markercluster` ships no type definitions — its dist folder contains
 * a file named WhereAreTheJavascriptFiles.txt and no .d.ts — and it augments
 * the L namespace at runtime. The two members used here are named rather than
 * reached for through `any`, which is the whole difference between "untyped
 * dependency" and "untyped code".
 */
interface ClusterGroup extends L.Layer {
  addLayers(layers: L.Layer[]): this;
  clearLayers(): this;
}
/** What `iconCreateFunction` is handed: the cluster, and what is inside it. */
interface Cluster {
  getChildCount(): number;
  getAllChildMarkers(): SourcedMarker[];
}
interface ClusterOptions {
  iconCreateFunction(cluster: Cluster): L.DivIcon;
}
interface WithMarkerCluster {
  MarkerClusterGroup: new (options: ClusterOptions) => ClusterGroup;
}
function markerClusterGroup(options: ClusterOptions): ClusterGroup {
  const { MarkerClusterGroup } = L as unknown as WithMarkerCluster;
  return new MarkerClusterGroup(options);
}

/** A marker that remembers which source it came from, for the cluster colour. */
type SourcedMarker = L.Marker & { ohmSource?: NetworkSpace["source"] };

// Vector div-icons (a colored dot) avoid Leaflet's broken default-marker asset
// paths under Vite, are colorable by source, and are still real L.Markers so
// react-leaflet-cluster can cluster them (CircleMarkers are not clustered).
// Keyed by source AND colour: keyed by source alone, the cache would pin the
// first world's hue and the map would stop re-theming.
const _iconCache: Record<string, L.DivIcon> = {};
function dotIcon(source: NetworkSpace["source"]): L.DivIcon {
  const color = sourceColor(source);
  const key = `${source}:${color}`;
  if (!_iconCache[key]) {
    // 24x24 icon, 12px dot. Leaflet markers are focusable targets, so a 12px
    // icon is a 12px target — under the WCAG 2.5.8 minimum, which the
    // narrow-viewport lane measures. The dot stays 12px so the map reads the
    // same; the extra 6px on each side is transparent hit area, centred so the
    // anchor still lands on the coordinate.
    _iconCache[key] = L.divIcon({
      className: "",
      html:
        `<span style="display:flex;align-items:center;justify-content:center;width:24px;height:24px">` +
        `<span style="display:block;width:12px;height:12px;border-radius:9999px;background:${color};border:1.5px solid white;box-shadow:0 0 3px rgba(0,0,0,0.5)"></span>` +
        `</span>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
    });
  }
  return _iconCache[key]!;
}

/**
 * A cluster bubble, drawn in the colour of what is inside it.
 *
 * The plugin ships its own green/amber/orange palette keyed to how many points
 * a bubble holds. That put three colours on a map whose key names two, none of
 * them matching either — the legend described markers the reader could barely
 * find among the bubbles, and the bubbles encoded a quantity the number in the
 * middle already gives. Size carries the count; colour carries the source,
 * which is the one thing the key is about.
 *
 * A cluster holding any local facility is drawn as local. Majority would be
 * the obvious rule and is the wrong one here: an instance has nine facilities
 * against three thousand federated spaces, so local never wins a bubble and
 * the key's first colour never appears on the map at all. The question this
 * map answers is "where are ours", and the rare thing has to survive being
 * grouped with the common one.
 */
function clusterIcon(cluster: Cluster): L.DivIcon {
  const count = cluster.getChildCount();
  const hasLocal = cluster
    .getAllChildMarkers()
    .some((marker) => marker.ohmSource === "local");
  const color = sourceColor(hasLocal ? "local" : "mom");

  // Area, not radius, tracks the count: doubling the points should look like
  // twice as much, and a linear radius makes a 2,000-point bubble swallow the
  // continent it sits on. Clamped either end so a pair is still hittable and a
  // continent-sized cluster stays a marker.
  const size = Math.round(
    Math.min(56, Math.max(28, 24 + Math.sqrt(count) * 2.2)),
  );

  return L.divIcon({
    className: "ohm-cluster",
    html:
      `<span style="display:flex;align-items:center;justify-content:center;` +
      `width:${size}px;height:${size}px;border-radius:9999px;` +
      `background:${color};color:var(--ttm-on-accent);` +
      `border:2px solid var(--card);` +
      `box-shadow:0 0 0 2px color-mix(in srgb, ${color} 35%, transparent);` +
      `font:600 ${size < 34 ? 11 : 12}px/1 var(--ttm-font-sans);` +
      `">${count.toLocaleString()}</span>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

/**
 * The popup for one space, built when it is opened rather than when the map is
 * drawn.
 *
 * Composed with textContent, not an HTML string: these names and cities come
 * from federated peers, so they are user-supplied text and must reach the DOM
 * as text.
 */
function popupContent(space: NetworkSpace): HTMLElement {
  const root = document.createElement("div");

  const name = document.createElement("strong");
  name.textContent = space.name;
  root.append(name, document.createElement("br"));

  const source = document.createElement("span");
  source.textContent = SOURCE_STYLES[space.source].label;
  root.append(source);

  if (space.city) {
    const place = document.createElement("span");
    place.textContent = [
      space.city,
      space.country ? displayCountryName(space.country) : null,
    ]
      .filter(Boolean)
      .join(", ");
    root.append(document.createElement("br"), place);
  }

  return root;
}

/**
 * Every space as one clustered marker layer, built imperatively.
 *
 * This was 3,202 <Marker> elements each wrapping a <Popup>, and the cost was
 * measurable: mounting the map blocked the main thread for ~390ms in two long
 * tasks, on the dashboard at load and again on every switch into map view.
 * Almost none of that was Leaflet. It was React creating and reconciling four
 * elements per space, and react-leaflet rendering 3,202 popup bodies for the
 * at most one a visitor ever opens.
 *
 * The markers are not interactive React content — they are a projection of an
 * array onto a canvas-like layer — so they are built directly, and the popup
 * body is deferred to a function Leaflet calls on open. Same clustering (the
 * plugin underneath react-leaflet-cluster), same icons, no React in the
 * per-space path.
 */
function SpaceMarkers({ spaces }: { spaces: NetworkSpace[] }) {
  const map = useMap();
  // Rebuilt when the world changes, not only when the data does. Marker and
  // cluster colours are read from the live tokens at build time, so without
  // this the map kept the previous world's palette until the space set
  // happened to change — which on the dashboard is never.
  const colors = useSourceColors();

  useEffect(() => {
    const markers = spaces.map((space) => {
      const marker: SourcedMarker = L.marker([space.lat, space.lon], {
        icon: dotIcon(space.source),
        title: space.name,
        alt: space.name,
      });
      // Stashed on the marker so a cluster can colour itself by what it holds
      // without a second lookup structure to keep in step with the layer.
      marker.ohmSource = space.source;
      marker.bindPopup(() => popupContent(space));
      return marker;
    });

    // addLayers, not addLayer in a loop, and no chunked loading. Chunked
    // loading spreads the insert across animation frames, which puts it in a
    // race with the fit below — and losing that race is silent: the cluster
    // tree is built against a zoom that changed underneath it and the layer
    // comes up holding a handful of the 3,202 markers. The bulk insert is one
    // synchronous pass with nothing to interleave with.
    const group = markerClusterGroup({ iconCreateFunction: clusterIcon });
    group.addLayers(markers);
    map.addLayer(group);

    return () => {
      map.removeLayer(group);
      group.clearLayers();
    };
  }, [map, spaces, colors]);
  return null;
}

/** Fit the viewport to the loaded spaces whenever the set changes. */
function FitBounds({ spaces }: { spaces: NetworkSpace[] }) {
  const map = useMap();
  useEffect(() => {
    if (spaces.length === 0) return;
    const size = map.getSize();
    if (size.x === 0 || size.y === 0) return;

    const pad = fitPadding(size.x, size.y);
    const floor = fillZoom(size.x, size.y);
    const full = L.latLngBounds(
      spaces.map((s) => [s.lat, s.lon] as [number, number]),
    );
    // A worldwide set fits a desktop panel at zoom 2 and a phone only at zoom
    // 0 — a 256px world adrift in grey, which is what "loads zoomed way out"
    // is. When the whole extent cannot be framed at a zoom that at least fills
    // the container, frame where the network is densest instead and leave the
    // rest one pinch away: the floor below is exactly the zoom that shows as
    // much of the world as the container can hold.
    //
    // Measured with the floor lifted: getBoundsZoom clamps its answer to the
    // map's current minZoom, so once a previous run has raised it, every later
    // run is told the world fits — a background refetch was enough to undo the
    // framing and leave the phone back at a whole-world view.
    map.setMinZoom(0);
    const fits = map.getBoundsZoom(full, false, L.point(pad, pad)) >= floor;
    // Raised before fitting so fitBounds clamps to it rather than being undone.
    map.setMinZoom(floor);
    map.fitBounds(fits ? full : L.latLngBounds(denseBounds(spaces)), {
      padding: [pad, pad],
      maxZoom: 12,
    });
  }, [map, spaces]);

  // A phone rotated to landscape is a differently-shaped container, and the
  // floor computed for the portrait one would let it zoom back out into grey.
  useEffect(() => {
    const onResize = () => {
      const size = map.getSize();
      if (size.x > 0 && size.y > 0) map.setMinZoom(fillZoom(size.x, size.y));
    };
    map.on("resize", onResize);
    return () => {
      map.off("resize", onResize);
    };
  }, [map]);

  return null;
}

/**
 * One finger scrolls the page, two fingers move the map.
 *
 * Leaflet's default — one-finger drag pans — makes a map embedded in a
 * scrolling page a trap on a phone: on the dashboard the map is the first
 * thing under the heading, so the swipe that meant "scroll down" drags the map
 * and the page never moves. Dropping the drag handler hands that gesture back
 * to the browser (Leaflet's own CSS switches the container to
 * `touch-action: pan-x pan-y` the moment dragging is off) and leaves panning
 * on the two-finger gesture, which its touch-zoom handler already re-centres
 * on the moving midpoint.
 *
 * Gated on the pointer, not the user agent: a narrow desktop window is not a
 * touch device, and that is the width the responsive lane measures.
 */
function TouchGestures({ onOneFinger }: { onOneFinger: () => void }) {
  const map = useMap();
  useEffect(() => {
    if (!window.matchMedia("(pointer: coarse)").matches) return;
    map.dragging.disable();
    const el = map.getContainer();
    const onTouchMove = (e: TouchEvent) => {
      if (e.touches.length === 1) onOneFinger();
    };
    el.addEventListener("touchmove", onTouchMove, { passive: true });
    return () => {
      el.removeEventListener("touchmove", onTouchMove);
      map.dragging.enable();
    };
  }, [map, onOneFinger]);
  return null;
}

/** A flag that raises itself on demand and lowers itself a moment later. */
function useTransientFlag(ms: number): [boolean, () => void] {
  const [on, setOn] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const raise = useCallback(() => {
    setOn(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setOn(false), ms);
  }, [ms]);
  useEffect(
    () => () => {
      if (timer.current) clearTimeout(timer.current);
    },
    [],
  );
  return [on, raise];
}

export function NetworkMap({ spaces }: { spaces: NetworkSpace[] }) {
  const [showHint, raiseHint] = useTransientFlag(2400);
  // Same resolver the markers and the key read, so the ground and the points
  // on it cannot come from two different worlds — which is the failure the
  // hook's own comment describes, one level up.
  const { tiles } = useSourceColors();
  return (
    <div
      className="relative h-full w-full"
      style={{ "--ohm-tile-filter": tiles } as CSSProperties}
    >
      <MapContainer
        center={[20, 0]}
        zoom={2}
        scrollWheelZoom
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <SpaceMarkers spaces={spaces} />
        <FitBounds spaces={spaces} />
        <TouchGestures onOneFinger={raiseHint} />
      </MapContainer>
      {showHint && (
        <p
          role="status"
          className="pointer-events-none absolute inset-x-4 bottom-4 z-[1000] rounded-md border border-border bg-card/95 px-3 py-2 text-center text-sm text-foreground shadow-md"
        >
          Use two fingers to move the map
        </p>
      )}
    </div>
  );
}
