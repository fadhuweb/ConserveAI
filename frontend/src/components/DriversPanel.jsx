import { ArrowUpOutlined, ArrowDownOutlined } from "@ant-design/icons";

const THREATS = [
  ["fire", "🔥 Fire", "#E64A19"],
  ["drought", "💧 Drought", "#1976D2"],
  ["vegetation", "🌿 Vegetation", "#388E3C"],
];

// Plain-language forecast drivers: which features raise/lower each threat.
export default function DriversPanel({ drivers }) {
  if (!drivers) return <p className="muted">Loading drivers…</p>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
      {THREATS.map(([key, label, color]) => (
        <div key={key}>
          <div style={{ fontWeight: 600, color, marginBottom: 8 }}>{label}</div>
          {(drivers[key] || []).map((d, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
              padding: "6px 0", borderBottom: "1px solid #F0F2F5", fontSize: 13 }}>
              <span className="muted">{d.label}</span>
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <b>{d.value}</b>
                {d.impact === "raises"
                  ? <ArrowUpOutlined style={{ color: "#D32F2F" }} title="raises risk" />
                  : <ArrowDownOutlined style={{ color: "#43A047" }} title="lowers risk" />}
              </span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
