import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import type { MapPoint } from "../../api/ohm/map";
import { SOURCE_STYLES } from "./mapSummary";

// Vector div-icons (a colored dot) avoid Leaflet's broken default-marker asset
// paths under Vite, are colorable by source, and are still real L.Markers so
// react-leaflet-cluster can cluster them (CircleMarkers are not clustered).
const _iconCache: Partial<Record<MapPoint["source"], L.DivIcon>> = {};
function dotIcon(source: MapPoint["source"]): L.DivIcon {
  if (!_iconCache[source]) {
    const color = SOURCE_STYLES[source].color;
    _iconCache[source] = L.divIcon({
      className: "",
      html: `<span style="display:block;width:12px;height:12px;border-radius:9999px;background:${color};border:1.5px solid white;box-shadow:0 0 3px rgba(0,0,0,0.5)"></span>`,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
    });
  }
  return _iconCache[source]!;
}

/** Fit the viewport to the loaded points once they arrive. */
function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length === 0) return;
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number]));
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
  }, [map, points]);
  return null;
}

export function NetworkMap({ points }: { points: MapPoint[] }) {
  return (
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
      {/* Re-key on the point count so the cluster layer rebuilds when data loads. */}
      <MarkerClusterGroup key={points.length} chunkedLoading>
        {points.map((p) => (
          <Marker
            key={`${p.source}-${p.id}`}
            position={[p.lat, p.lon]}
            icon={dotIcon(p.source)}
            // Accessible name for the focusable marker (the dot has no text).
            title={p.name}
            alt={p.name}
          >
            <Popup>
              <strong>{p.name}</strong>
              <br />
              <span>{SOURCE_STYLES[p.source].label}</span>
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>
      <FitBounds points={points} />
    </MapContainer>
  );
}
