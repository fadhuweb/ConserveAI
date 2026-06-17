import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

const LINES = [["Fire", "#E64A19"], ["Drought", "#1976D2"], ["Vegetation", "#388E3C"]];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: "rgba(15, 23, 42, 0.95)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        padding: "12px 16px",
        borderRadius: "12px",
        boxShadow: "0 10px 25px rgba(0, 0, 0, 0.3)",
        backdropFilter: "blur(8px)"
      }}>
        <p style={{ margin: "0 0 8px 0", color: "#94a3b8", fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.08em" }}>{label}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          {payload.map((entry) => (
            <div key={entry.name} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "24px" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", fontWeight: "500", color: "#f1f5f9" }}>
                <span style={{ display: "inline-block", width: "8px", height: "8px", borderRadius: "50%", background: entry.color }}></span>
                {entry.name}
              </span>
              <span style={{ fontSize: "14px", fontWeight: "700", color: entry.color }}>{entry.value}%</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

// Hybrid Line/Area forecast history: fire, drought, vegetation over the past ~60 days.
// `focus` (a series name) emphasises one threat and fades the others using gradients.
export default function ForecastChart({ forecasts, focus }) {
  const data = (forecasts || []).map((f) => ({
    date: f.date,
    Fire: Math.round(f.fire_prob * 100),
    Drought: Math.round(f.drought_prob * 100),
    Vegetation: Math.round(f.veg_prob * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <defs>
          <linearGradient id="colorFire" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#E64A19" stopOpacity={0.24}/>
            <stop offset="95%" stopColor="#E64A19" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorDrought" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#1976D2" stopOpacity={0.24}/>
            <stop offset="95%" stopColor="#1976D2" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorVegetation" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#388E3C" stopOpacity={0.24}/>
            <stop offset="95%" stopColor="#388E3C" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
        <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#64748B" }} minTickGap={40} tickLine={false} axisLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#64748B" }} unit="%" tickLine={false} axisLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: "12px", fontWeight: 500 }} />
        {LINES.map(([name, color]) => {
          const faded = focus && focus !== name;
          const isFocused = focus === name;
          return (
            <Area
              key={name}
              type="monotone"
              dataKey={name}
              stroke={color}
              fill={`url(#color${name})`}
              fillOpacity={isFocused ? 1 : faded ? 0 : 0.05}
              strokeWidth={isFocused ? 3 : 2}
              strokeOpacity={faded ? 0.16 : 1}
              isAnimationActive={false}
            />
          );
        })}
      </AreaChart>
    </ResponsiveContainer>
  );
}
