import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";

// Three-line forecast history: fire, drought, vegetation over the past ~60 days.
export default function ForecastChart({ forecasts }) {
  const data = (forecasts || []).map((f) => ({
    date: f.date,
    Fire: Math.round(f.fire_prob * 100),
    Drought: Math.round(f.drought_prob * 100),
    Vegetation: Math.round(f.veg_prob * 100),
  }));

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EEF1F5" />
        <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} unit="%" />
        <Tooltip formatter={(v) => `${v}%`} />
        <Legend />
        <Line type="monotone" dataKey="Fire" stroke="#E64A19" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Drought" stroke="#1976D2" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="Vegetation" stroke="#388E3C" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
