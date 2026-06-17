import { Tooltip } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";

const THREATS = [
  ["fire", "Fire", "#E64A19"],
  ["drought", "Drought", "#1976D2"],
  ["vegetation", "Vegetation", "#388E3C"],
];

// Plain-language definition of each signal, shown on hover (ⓘ).
const HELP = {
  "30-day rainfall": "Total rainfall over the last 30 days, compared to a 20 mm dry-threshold. Above it eases fire and drought; below it raises them.",
  "Rainfall deficit (30d)": "Recent rainfall versus the seasonal normal for this park. Negative means a shortfall (less rain than usual), which raises drought risk — even when raw rainfall looks okay.",
  "60-day rainfall": "Total rainfall over the last 60 days, vs a 50 mm threshold — a longer-term moisture check.",
  "Dry season": "Whether today falls in the dry season (roughly Nov–Apr in the north). Dry season raises both fire and drought risk.",
  "Avg max temperature": "Average daily high temperature over the last 30 days, vs 34 °C. Hotter, drier air cures vegetation into fuel and raises fire risk.",
  "Days since last fire": "Days since the last fire was detected here. Long gaps mean fuel has built up unburned, raising fire risk.",
  "Vegetation index (NDVI)": "Satellite-measured greenness (0–1). Lower values mean sparser, drier vegetation — i.e. higher vegetation stress.",
  "NDVI vs 90-day normal": "Current greenness versus its own 90-day average. Negative means vegetation is below its usual level for the park.",
  "NDVI change (30d)": "How much greenness has changed over the last 30 days. A decline (negative) signals vegetation drying out or being cleared.",
};

// Plain-language forecast drivers: which environmental signals raise/lower each threat.
// `focus` (a threat key) narrows the panel to a single threat.
export default function DriversPanel({ drivers, focus }) {
  if (!drivers) return <p className="muted">Loading drivers…</p>;

  const shown = focus ? THREATS.filter(([k]) => k === focus) : THREATS;

  return (
    <>
      <p className="muted" style={{ marginTop: -2, marginBottom: 16, fontSize: 13 }}>
        The environmental signals currently pushing {focus ? "this" : "each"} 30-day threat up or down. A
        red <b>Raises</b> tag means that reading is increasing the risk; a green <b>Lowers</b> tag
        means it is easing it.
      </p>
      <div className="drivers-grid" style={focus ? { gridTemplateColumns: "1fr" } : undefined}>
        {shown.map(([key, label, color]) => (
          <div key={key} className="drivers-col">
            <div className="drivers-head" style={{ color }}>{label}</div>
            {(drivers[key] || []).map((d, i) => (
              <div key={i} className="driver-row">
                <div className="driver-meta">
                  <span className="driver-label">
                    {d.label}
                    {HELP[d.label] && (
                      <Tooltip title={HELP[d.label]}>
                        <InfoCircleOutlined className="driver-info" />
                      </Tooltip>
                    )}
                  </span>
                  <span className="driver-value">{d.value}</span>
                </div>
                <span className={`driver-tag ${d.impact === "raises" ? "up" : "down"}`}>
                  {d.impact === "raises" ? "Raises" : "Lowers"}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
