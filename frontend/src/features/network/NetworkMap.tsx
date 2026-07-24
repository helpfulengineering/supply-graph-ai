import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import type { NetworkSpace } from "../../api/ohm/network";
import { SOURCE_STYLES } from "./networkSummary";
import { displayCountryName } from "../match/geoDisplay";

// Vector div-icons (a colored dot) avoid Leaflet's broken default-marker asset
// paths under Vite, are colorable by source, and are still real L.Markers so
// react-leaflet-cluster can cluster them (CircleMarkers are not clustered).
const _iconCache: Partial<Record<NetworkSpace["source"], L.DivIcon>> = {};
function dotIcon(source: NetworkSpace["source"]): L.DivIcon {
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

/** Fit the viewport to the loaded spaces whenever the set changes. */
function FitBounds({ spaces }: { spaces: NetworkSpace[] }) {
  const map = useMap();
  useEffect(() => {
    if (spaces.length === 0) return;
    const bounds = L.latLngBounds(spaces.map((s) => [s.lat, s.lon] as [number, number]));
    map.fitBounds(bounds, { padding: [30, 30], maxZoom: 12 });
  }, [map, spaces]);
  return null;
}

export function NetworkMap({ spaces }: { spaces: NetworkSpace[] }) {
  return (
    <MapContainer center={[20, 0]} zoom={2} scrollWheelZoom className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {/* Re-key on the space count so the cluster layer rebuilds when data changes. */}
      <MarkerClusterGroup key={spaces.length} chunkedLoading>
        {spaces.map((s) => (
          <Marker
            key={`${s.source}-${s.id}`}
            position={[s.lat, s.lon]}
            icon={dotIcon(s.source)}
            title={s.name}
            alt={s.name}
          >
            <Popup>
              <strong>{s.name}</strong>
              <br />
              <span>{SOURCE_STYLES[s.source].label}</span>
              {s.city && (
                <>
                  <br />
                  <span>
                    {[s.city, s.country ? displayCountryName(s.country) : null]
                      .filter(Boolean)
                      .join(", ")}
                  </span>
                </>
              )}
            </Popup>
          </Marker>
        ))}
      </MarkerClusterGroup>
      <FitBounds spaces={spaces} />
    </MapContainer>
  );
}
