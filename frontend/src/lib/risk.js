// Shared risk-level helpers used by the overview and park-detail screens.

// A tiny risk is real but imprecise: the model does not meaningfully distinguish
// 0.3% from 0.9% at the low end, so claiming one decimal there is false precision.
// Show "<1%" for anything positive under 1% (honest: non-zero but very low, not "0%"),
// one decimal for the 1-10% band where the gap is meaningful, and whole numbers above.
export const pct = (p) => {
  const v = (p ?? 0) * 100;
  if (v <= 0) return "0%";
  if (v < 1) return "<1%";
  if (v < 10) return `${v.toFixed(1)}%`;
  return `${Math.round(v)}%`;
};

// Single risk palette — these MUST mirror the --hi / --med / --lo CSS variables
// in index.css so the map, gauges, bars, table and legend all use the same colours.
export function riskColor(p) {
  if (p >= 0.66) return "#ef4444"; // high
  if (p >= 0.33) return "#f59e0b"; // medium
  return "#10b981";                // low
}

export function riskLabel(p) {
  if (p >= 0.66) return "High";
  if (p >= 0.33) return "Medium";
  return "Low";
}
