import { MapContainer, TileLayer, Rectangle, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";

// Zoned park map: draws the four zone rectangles. When a recommendation exists,
// each zone is shaded by how many units it received; otherwise neutral.
export default function ParkMap({ zones, zoneAllocations }) {
  if (!zones || zones.length === 0) return <p className="muted">No zones defined.</p>;

  // total units per zone from the latest recommendation
  const unitsByZone = {};
  (zoneAllocations || []).forEach((a) => {
    unitsByZone[a.zone_id] = (unitsByZone[a.zone_id] || 0) + a.units;
  });
  const maxUnits = Math.max(1, ...Object.values(unitsByZone));

  // center on the park (mean of zone bboxes)
  const lat = zones.reduce((s, z) => s + (z.min_lat + z.max_lat) / 2, 0) / zones.length;
  const lon = zones.reduce((s, z) => s + (z.min_lon + z.max_lon) / 2, 0) / zones.length;

  const shade = (zoneId) => {
    const u = unitsByZone[zoneId] || 0;
    if (!zoneAllocations || zoneAllocations.length === 0) return 0.15;
    return 0.15 + 0.55 * (u / maxUnits);
  };

  return (
    <MapContainer center={[lat, lon]} zoom={9} scrollWheelZoom={false} style={{ height: 300, width: "100%" }}>
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
        attribution="&copy; OpenStreetMap &copy; CARTO"
      />
      {zones.map((z) => (
        <Rectangle
          key={z.id}
          bounds={[[z.min_lat, z.min_lon], [z.max_lat, z.max_lon]]}
          pathOptions={{ color: "#1d6b4f", weight: 1.5, fillColor: "#1d6b4f", fillOpacity: shade(z.id) }}
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
