import { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, LayersControl } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { Card, Table, Button, Alert, Skeleton, Segmented } from "antd";
import AppShell from "../components/AppShell";
import NationalTrend from "../components/NationalTrend";
import PriorityParks from "../components/PriorityParks";
import parkBoundaries from "../data/parkBoundaries.json";
import { getParks, getNationalOverview, getNationalTrend } from "../api/forecasts";
import { riskColor, pct } from "../lib/risk";

const NIGERIA_CENTER = [9.0, 8.6];

// Marker positions are derived from the park's real boundary (same source as the
// polygons), so a marker is always centred on its park instead of drifting off it.
function ringCentroid(ring) {
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [x0, y0] = ring[i], [x1, y1] = ring[i + 1];
    const cross = x0 * y1 - x1 * y0;
    a += cross; cx += (x0 + x1) * cross; cy += (y0 + y1) * cross;
  }
  a *= 0.5;
  if (Math.abs(a) < 1e-9) {                       // degenerate → average the vertices
    const xs = ring.map((p) => p[0]), ys = ring.map((p) => p[1]);
    return [ys.reduce((s, v) => s + v, 0) / ys.length, xs.reduce((s, v) => s + v, 0) / xs.length];
  }
  return [cy / (6 * a), cx / (6 * a)];             // [lat, lon]
}
function featureCentroid(feature) {
  const g = feature.geometry;
  let ring = g.coordinates[0];
  if (g.type === "MultiPolygon") {                // use the largest polygon's outer ring
    g.coordinates.forEach((poly) => { if (poly[0].length > ring.length) ring = poly[0]; });
  }
  return ringCentroid(ring);
}
const PARK_CENTROID = Object.fromEntries(
  parkBoundaries.features.map((f) => [f.properties.park, featureCentroid(f)])
);

// Graphical threat gauge for table rows
const ThreatGauge = ({ p }) => {
  const color = riskColor(p);
  return (
    <div className="threat-gauge-container">
      <div className="threat-gauge-track">
        <div 
          className="threat-gauge-bar" 
          style={{ width: `${Math.round(p * 100)}%`, backgroundColor: color }}
        />
      </div>
      <span className="threat-gauge-pct" style={{ color: color }}>
        {pct(p)}
      </span>
    </div>
  );
};

export default function NationalOverview() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [trend, setTrend] = useState([]);
  const mapRef = useRef(null);
  const [lens, setLens] = useState("max");   // colour lens: max | fire | drought | vegetation

  useEffect(() => {
    Promise.all([getParks(), getNationalOverview(), getNationalTrend()])
      .then(([parks, overview, t]) => {
        const byId = Object.fromEntries(parks.map((p) => [p.id, p]));
        setRows(
          overview.map((o) => ({
            ...byId[o.park],
            ...o,
            key: o.park,
            maxRisk: Math.max(o.fire_prob, o.drought_prob, o.veg_prob),
          }))
        );
        setTrend(t);
      })
      .catch(() => setError("Failed to load the national overview."))
      .finally(() => setLoading(false));
  }, []);

  const highCount = rows.filter((r) => r.maxRisk >= 0.66).length;
  const avg = (k) => (rows.length ? rows.reduce((s, r) => s + r[k], 0) / rows.length : 0);
  const threats = [["Fire", avg("fire_prob")], ["Drought", avg("drought_prob")], ["Vegetation", avg("veg_prob")]];
  const dominant = threats.reduce((a, b) => (b[1] > a[1] ? b : a), threats[0]);
  const topPark = rows.length ? [...rows].sort((a, b) => b.maxRisk - a.maxRisk)[0] : null;
  // The single highest park × threat spike — the real "what needs attention", vs the average.
  const spike = rows.length
    ? rows.flatMap((r) => [["Fire", r.fire_prob], ["Drought", r.drought_prob], ["Vegetation", r.veg_prob]]
        .map(([t, v]) => ({ park: r.display_name || r.park, threat: t, v })))
        .sort((a, b) => b.v - a.v)[0]
    : null;
  const latestUpdate = rows.find((r) => r.latest_date)?.latest_date || "Pending";

  // value for the active threat lens ("max" = highest of the three)
  const lensValue = (r) => !r ? 0
    : lens === "fire" ? r.fire_prob
    : lens === "drought" ? r.drought_prob
    : lens === "vegetation" ? r.veg_prob
    : r.maxRisk;
  const focusPark = (r) => {
    const pos = PARK_CENTROID[r?.park] || (r?.lat != null ? [r.lat, r.lon] : null);
    if (pos && mapRef.current) {
      mapRef.current.flyTo(pos, 9, { duration: 0.8 });
      mapRef.current.getContainer().scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  // park boundary polygons, styled by the active lens
  const rowById = Object.fromEntries(rows.map((r) => [r.park, r]));
  const boundaryStyle = (feature) => {
    const r = rowById[feature.properties.park];
    const color = r ? riskColor(lensValue(r)) : "#9aa5b1";
    return {
      color, weight: 2, fillColor: color,
      fillOpacity: feature.properties.approx ? 0.10 : 0.28,
      dashArray: feature.properties.approx ? "5 5" : null,
    };
  };
  const onEachBoundary = (feature, layer) => {
    const r = rowById[feature.properties.park];
    const name = r?.display_name || feature.properties.name;
    const extra = feature.properties.approx ? "<br/><i>approx. area</i>" : "";
    layer.bindTooltip(
      `<b>${name}</b><br/>Fire ${r ? pct(r.fire_prob) : "–"} · Drought ${r ? pct(r.drought_prob) : "–"} · Veg ${r ? pct(r.veg_prob) : "–"}${extra}`,
      { sticky: true }
    );
    layer.on("click", () => focusPark(r));
  };

  const columns = [
    { 
      title: "Park", 
      dataIndex: "display_name", 
      key: "park",
      render: (v, r) => (
        <span className="park-link" onClick={() => focusPark(r)}>
          {v || r.park}
        </span>
      )
    },
    {
      title: "Fire Threat",
      dataIndex: "fire_prob",
      key: "fire",
      sorter: (a, b) => a.fire_prob - b.fire_prob,
      render: (p) => <ThreatGauge p={p} />
    },
    {
      title: "Drought Threat",
      dataIndex: "drought_prob",
      key: "drought",
      sorter: (a, b) => a.drought_prob - b.drought_prob,
      render: (p) => <ThreatGauge p={p} />
    },
    {
      title: "Vegetation Threat",
      dataIndex: "veg_prob",
      key: "veg",
      sorter: (a, b) => a.veg_prob - b.veg_prob,
      render: (p) => <ThreatGauge p={p} />
    },
    { 
      title: "Last Updated", 
      dataIndex: "latest_date", 
      key: "updated",
      render: (d) => <span style={{ color: "var(--muted)", fontWeight: 500 }}>{d}</span> 
    },
    {
      title: "Action",
      key: "action",
      render: (_, r) => (
        <Button
          className="action-btn"
          size="small"
          onClick={(e) => { e.stopPropagation(); focusPark(r); }}
        >
          Locate on map
        </Button>
      )
    }
  ];

  return (
    <AppShell subtitle="National Overview">
        <div className="ops-page-title">
          <div>
            <h2>National Operations Dashboard</h2>
            <p className="muted" style={{ marginTop: 6, fontSize: 14 }}>
              30-day fire, drought, and vegetation threat monitoring across Nigeria's national parks.
            </p>
          </div>
          <span className="ops-meta">Forecast updated {latestUpdate}</span>
        </div>

        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 24, borderRadius: 12 }} />}

        {loading ? (
          <div>
            <div className="dashboard-grid">
              {[1, 2, 3].map((i) => (
                <Card key={i}><Skeleton active title={false} paragraph={{ rows: 2 }} /></Card>
              ))}
            </div>
            <Card style={{ marginBottom: 24 }}><Skeleton active paragraph={{ rows: 3 }} /></Card>
            <Card style={{ marginBottom: 24 }}><Skeleton.Node active style={{ width: "100%", height: 360 }} /></Card>
            <Card><Skeleton active paragraph={{ rows: 4 }} /></Card>
          </div>
        ) : (
          <>
            <div className="ops-alert-strip ops-alert-strip-three">
              <div className="ops-alert-cell primary">
                <span className="ops-alert-label">Today needs attention</span>
                <span className="ops-alert-value">
                  {highCount ? `${highCount} high-risk ${highCount === 1 ? "park" : "parks"}` : "No high-risk parks"}
                </span>
                <span className="ops-alert-note">
                  {spike ? `Highest: ${spike.park} · ${spike.threat} ${pct(spike.v)}` : "Awaiting park forecasts."}
                </span>
              </div>
              <div className="ops-alert-cell">
                <span className="ops-alert-label">Dominant threat (avg)</span>
                <span className="ops-alert-value">{dominant[0]}</span>
                <span className="ops-alert-note">{pct(dominant[1])} national average</span>
              </div>
              <div className="ops-alert-cell">
                <span className="ops-alert-label">Parks monitored</span>
                <span className="ops-alert-value">{rows.length}</span>
                <span className="ops-alert-note">Active forecast coverage</span>
              </div>
            </div>

            <div className="ops-command-grid">
              <div>
                <Card title="National risk map" className="map-card"
                  styles={{ body: { padding: 0 } }}
                  extra={
                    <Segmented size="small" value={lens} onChange={setLens}
                      options={[
                        { label: "Highest", value: "max" },
                        { label: "Fire", value: "fire" },
                        { label: "Drought", value: "drought" },
                        { label: "Vegetation", value: "vegetation" },
                      ]} />
                  }
                >
                  <div className="map-wrap">
                    <MapContainer
                      ref={mapRef}
                      center={NIGERIA_CENTER}
                      zoom={6}
                      scrollWheelZoom={false}
                      style={{ height: 560, width: "100%" }}
                    >
                      <LayersControl position="topright">
                        <LayersControl.BaseLayer checked name="Map">
                          <TileLayer
                            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                            attribution='&copy; OpenStreetMap &copy; CARTO'
                          />
                        </LayersControl.BaseLayer>
                        <LayersControl.BaseLayer name="Satellite">
                          <TileLayer
                            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                            attribution="Tiles &copy; Esri"
                          />
                        </LayersControl.BaseLayer>
                        <LayersControl.BaseLayer name="Terrain">
                          <TileLayer
                            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
                            attribution="&copy; OpenTopoMap (CC-BY-SA)"
                          />
                        </LayersControl.BaseLayer>
                      </LayersControl>

                      <GeoJSON key={`${rows.length}-${lens}`} data={parkBoundaries} style={boundaryStyle} onEachFeature={onEachBoundary} />
                    </MapContainer>
                    <div className="map-legend">
                      <span><i style={{ background: "var(--lo)" }} /> Low</span>
                      <span><i style={{ background: "var(--med)" }} /> Medium</span>
                      <span><i style={{ background: "var(--hi)" }} /> High</span>
                    </div>
                  </div>
                </Card>
              </div>

              <div className="ops-stack">
                <Card title="National trend indicators" className="ops-card">
                  <NationalTrend data={trend} />
                </Card>

                <Card title="Priority parks" className="ops-card">
                  <PriorityParks rows={rows} onLocate={focusPark} />
                </Card>
              </div>
            </div>

            <Card title="Park threat forecast summary" className="table-card" style={{ marginTop: 16 }}>
              <Table
                columns={columns}
                dataSource={rows}
                pagination={false}
                size="middle"
                onRow={(record) => ({ onClick: () => focusPark(record) })}
              />
            </Card>
          </>
        )}
    </AppShell>
  );
}
