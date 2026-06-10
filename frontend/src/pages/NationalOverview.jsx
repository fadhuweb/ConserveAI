import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Tooltip } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Card, Row, Col, Table, Button, Alert, Spin } from "antd";
import { useNavigate } from "react-router-dom";
import { GlobalOutlined, WarningOutlined, ThunderboltOutlined } from "@ant-design/icons";
import TopBar from "../components/TopBar";
import { getParks, getNationalOverview } from "../api/forecasts";
import { riskColor, pct } from "../lib/risk";

const NIGERIA_CENTER = [9.0, 8.6];

// Custom HTML pulsing marker for the Leaflet map
const customMarkerIcon = (color) => L.divIcon({
  className: "custom-pulse-marker",
  html: `
    <div class="pulse-dot" style="background-color: ${color}"></div>
    <div class="pulse-ring" style="border-color: ${color}"></div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

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
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getParks(), getNationalOverview()])
      .then(([parks, overview]) => {
        const byId = Object.fromEntries(parks.map((p) => [p.id, p]));
        setRows(
          overview.map((o) => ({
            ...byId[o.park],
            ...o,
            key: o.park,
            maxRisk: Math.max(o.fire_prob, o.drought_prob, o.veg_prob),
          }))
        );
      })
      .catch(() => setError("Failed to load the national overview."))
      .finally(() => setLoading(false));
  }, []);

  const highCount = rows.filter((r) => r.maxRisk >= 0.66).length;
  const avg = (k) => (rows.length ? rows.reduce((s, r) => s + r[k], 0) / rows.length : 0);
  const threats = [["Fire", avg("fire_prob")], ["Drought", avg("drought_prob")], ["Vegetation", avg("veg_prob")]];
  const dominant = threats.reduce((a, b) => (b[1] > a[1] ? b : a), threats[0]);

  const getThreatIcon = (name) => {
    if (name === "Fire") return "🔥";
    if (name === "Drought") return "💧";
    return "🌿";
  };

  const columns = [
    { 
      title: "Park", 
      dataIndex: "display_name", 
      key: "park",
      render: (v, r) => (
        <span className="park-link" onClick={() => navigate(`/park/${r.park}`)}>
          🌳 {v || r.park}
        </span>
      ) 
    },
    { 
      title: "Fire Threat", 
      dataIndex: "fire_prob", 
      key: "fire", 
      render: (p) => <ThreatGauge p={p} /> 
    },
    { 
      title: "Drought Threat", 
      dataIndex: "drought_prob", 
      key: "drought", 
      render: (p) => <ThreatGauge p={p} /> 
    },
    { 
      title: "Vegetation Threat", 
      dataIndex: "veg_prob", 
      key: "veg", 
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
          onClick={() => navigate(`/park/${r.park}`)}
        >
          View details →
        </Button>
      )
    }
  ];

  return (
    <div className="page">
      <TopBar subtitle="National Overview" />

      <main className="content">
        <div style={{ marginBottom: 24 }}>
          <h2>National Overview</h2>
          <p className="muted" style={{ marginTop: 6, fontSize: 15 }}>
            Consolidated 30-day probabilistic risk analysis across Nigeria's six national parks. Click any park to manage.
          </p>
        </div>

        {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 24, borderRadius: 12 }} />}

        {loading ? (
          <div style={{ padding: 100, textAlign: "center" }}><Spin size="large" /></div>
        ) : (
          <>
            {/* Stat Cards Section */}
            <div className="dashboard-grid">
              <div className="stat-card brand-top animate-fade-in-up">
                <div className="stat-card-left">
                  <span className="stat-card-title">Parks monitored</span>
                  <span className="stat-card-value">{rows.length}</span>
                  <span className="stat-card-sub">Active telemetry nodes</span>
                </div>
                <div className="stat-card-icon" style={{ background: "rgba(32, 92, 72, 0.08)", color: "var(--brand)" }}>
                  <GlobalOutlined />
                </div>
              </div>

              <div className="stat-card danger-top animate-fade-in-up delay-1">
                <div className="stat-card-left">
                  <span className="stat-card-title">High-risk parks</span>
                  <span className="stat-card-value" style={{ color: highCount ? "var(--hi)" : "inherit" }}>
                    {highCount}
                    {highCount > 0 && <span className="warning-pulse"></span>}
                  </span>
                  <span className="stat-card-sub">Require threat mitigation</span>
                </div>
                <div className="stat-card-icon" style={{ background: "rgba(211, 47, 47, 0.08)", color: "var(--hi)" }}>
                  <WarningOutlined />
                </div>
              </div>

              <div className="stat-card glow-top animate-fade-in-up delay-2">
                <div className="stat-card-left">
                  <span className="stat-card-title">Dominant threat</span>
                  <span className="stat-card-value" style={{ color: "var(--brand)" }}>
                    {getThreatIcon(dominant[0])} {dominant[0]}
                  </span>
                  <span className="stat-card-sub">{pct(dominant[1])} average probability</span>
                </div>
                <div className="stat-card-icon" style={{ background: "rgba(249, 168, 37, 0.08)", color: "var(--med)" }}>
                  <ThunderboltOutlined />
                </div>
              </div>
            </div>

            {/* Interactive Map Card */}
            <Card title="Interactive Risk Map" className="map-card animate-fade-in-up delay-1" styles={{ body: { padding: 0 } }}>
              <MapContainer 
                center={NIGERIA_CENTER} 
                zoom={6} 
                scrollWheelZoom={false}
                style={{ height: 480, width: "100%" }}
              >
                {/* Beautiful clean high-contrast tile layer from CartoDB */}
                <TileLayer 
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />
                {rows.filter((r) => r.lat != null).map((r) => (
                  <Marker 
                    key={r.park} 
                    position={[r.lat, r.lon]} 
                    icon={customMarkerIcon(riskColor(r.maxRisk))}
                    eventHandlers={{
                      click: () => navigate(`/park/${r.park}`),
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -10]} opacity={1}>
                      <div className="tooltip-title">{r.display_name || r.park}</div>
                      <div className="tooltip-row">
                        <span>🔥 Fire Risk:</span>
                        <span className="tooltip-val" style={{ color: riskColor(r.fire_prob) }}>{pct(r.fire_prob)}</span>
                      </div>
                      <div className="tooltip-row">
                        <span>💧 Drought Risk:</span>
                        <span className="tooltip-val" style={{ color: riskColor(r.drought_prob) }}>{pct(r.drought_prob)}</span>
                      </div>
                      <div className="tooltip-row">
                        <span>🌿 Vegetation Degradation:</span>
                        <span className="tooltip-val" style={{ color: riskColor(r.veg_prob) }}>{pct(r.veg_prob)}</span>
                      </div>
                      <div className="tooltip-prompt">Click to open dashboard</div>
                    </Tooltip>
                  </Marker>
                ))}
              </MapContainer>
            </Card>

            {/* Parks Forecasts List */}
            <Card title="Parks Threat Forecast Summary" className="table-card animate-fade-in-up delay-2">
              <Table 
                columns={columns} 
                dataSource={rows} 
                pagination={false} 
                size="large"
              />
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
