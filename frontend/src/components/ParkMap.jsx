import { MapContainer, TileLayer, Rectangle, Tooltip, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import parkBoundaries from "../data/parkBoundaries.json";

// Flatten any GeoJSON coordinate nesting to [lon, lat] pairs.
function flatten(coords, out) {
  if (typeof coords[0] === "number") out.push(coords);
  else coords.forEach((c) => flatten(c, out));
  return out;
}

// Zoned park map: the real WDPA boundary as a backdrop, with the four zone
// rectangles on top — each shaded by how many intervention units it received.
export default function ParkMap({ parkId, zones, zoneAllocations, height = 320 }) {
  if (!zones || zones.length === 0) return <p className="muted">No zones defined.</p>;

  const boundary = parkBoundaries.features.find((f) => f.properties.park === parkId);

  const unitsByZone = {};
  (zoneAllocations || []).forEach((a) => {
    unitsByZone[a.zone_id] = (unitsByZone[a.zone_id] || 0) + a.units;
  });
  const maxUnits = Math.max(1, ...Object.values(unitsByZone));

  // Fit to the zone boxes plus the real boundary (if present), so nothing clips.
  const pts = zones.flatMap((z) => [[z.min_lat, z.min_lon], [z.max_lat, z.max_lon]]);
  if (boundary) flatten(boundary.geometry.coordinates, []).forEach(([lon, lat]) => pts.push([lat, lon]));
  const lats = pts.map((p) => p[0]);
  const lons = pts.map((p) => p[1]);
  const bounds = [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]];

  const shade = (zoneId) => {
    const u = unitsByZone[zoneId] || 0;
    if (!zoneAllocations || zoneAllocations.length === 0) return 0.15;
    return 0.15 + 0.55 * (u / maxUnits);
  };

  return (
    <MapContainer bounds={bounds} boundsOptions={{ padding: [25, 25] }} scrollWheelZoom={false}
                  style={{ height, width: "100%" }}>
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution="&copy; OpenStreetMap &copy; CARTO"
      />
      {boundary && (
        <GeoJSON
          data={boundary}
          style={{
            color: "#064e3b", weight: 2,
            dashArray: boundary.properties.approx ? "6 5" : null,
            fillColor: "#064e3b", fillOpacity: 0.06,
          }}
        >
          <Tooltip sticky>
            {boundary.properties.name}
            {boundary.properties.approx && " — approximate extent"}
          </Tooltip>
        </GeoJSON>
      )}
      {zones.map((z) => (
        <Rectangle
          key={z.id}
          bounds={[[z.min_lat, z.min_lon], [z.max_lat, z.max_lon]]}
          pathOptions={{ color: "#064e3b", weight: 1.5, fillColor: "#10b981", fillOpacity: shade(z.id) }}
        >
          <Tooltip direction="center" permanent>
            <div style={{ textAlign: "center", fontSize: 11 }}>
              <b>{z.name}</b>
              {unitsByZone[z.id] != null && <div>{unitsByZone[z.id]} units</div>}
            </div>
          </Tooltip>
        </Rectangle>
      ))}
    </MapContainer>
  );
}
