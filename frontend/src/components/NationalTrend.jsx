import { AreaChart, Area, ResponsiveContainer, YAxis, Tooltip } from "recharts";
import { riskColor, pct } from "../lib/risk";

const THREATS = [
  ["fire", "Fire", "#E64A19", "colorTrendFire"],
  ["drought", "Drought", "#1976D2", "colorTrendDrought"],
  ["veg", "Vegetation", "#388E3C", "colorTrendVeg"]
];

// Custom sparkline tooltip matching the overall professional dashboard theme
const SparklineTooltip = ({ active, payload, label, threatLabel, color }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: "rgba(15, 23, 42, 0.95)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        padding: "6px 10px",
        borderRadius: "8px",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.25)",
        backdropFilter: "blur(4px)"
      }}>
        <div style={{ fontSize: "11px", fontWeight: "700", color: "#94a3b8", marginBottom: "2px" }}>{label}</div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", fontWeight: "600", color: "#f1f5f9" }}>
          <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: color }}></span>
          <span>{threatLabel}: {pct(payload[0].value)}</span>
        </div>
      </div>
    );
  }
  return null;
};

// Three sparklines of the national daily-average risk, with a week-over-week delta.
export default function NationalTrend({ data }) {
  if (!data || data.length === 0) return <p className="muted">No trend data yet.</p>;
  const latest = data[data.length - 1];
  const weekAgo = data[Math.max(0, data.length - 8)];   // ~7 days earlier

  return (
    <div className="trend-row">
      {THREATS.map(([k, label, color, gradId]) => {
        const dp = Math.round((latest[k] - (weekAgo?.[k] ?? latest[k])) * 100);
        const dir = dp === 0 ? "flat" : dp > 0 ? "up" : "down";   // up = risk rising (bad)
        return (
          <div className="trend-tile" key={k} style={{ background: "#ffffff", overflow: "hidden" }}>
            <div className="trend-head" style={{ marginBottom: "8px" }}>
              <span className="trend-label" style={{ color: "#64748B", fontWeight: 600 }}>{label}</span>
              <span className="trend-cur" style={{ color: riskColor(latest[k]), fontWeight: 800 }}>{pct(latest[k])}</span>
            </div>
            <ResponsiveContainer width="100%" height={50}>
              <AreaChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={color} stopOpacity={0.25}/>
                    <stop offset="95%" stopColor={color} stopOpacity={0.01}/>
                  </linearGradient>
                </defs>
                <YAxis domain={[0, 1]} hide />
                <Tooltip
                  content={<SparklineTooltip threatLabel={label} color={color} />}
                  labelFormatter={(idx) => data[idx]?.date || ""}
                />
                <Area 
                  type="monotone" 
                  dataKey={k} 
                  stroke={color} 
                  fill={`url(#${gradId})`} 
                  strokeWidth={2} 
                  dot={false} 
                  isAnimationActive={false} 
                />
              </AreaChart>
            </ResponsiveContainer>
            <div className="trend-sub" style={{ marginTop: "6px" }}>
              <span className={`trend-delta ${dir}`} style={{ fontWeight: 700 }}>
                {dp === 0 ? "no change" : `${dp > 0 ? "▲" : "▼"} ${Math.abs(dp)}%`}
              </span>
              <span className="muted"> vs last week</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
