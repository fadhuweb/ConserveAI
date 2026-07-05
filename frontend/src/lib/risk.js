// Shared risk-level helpers used by the overview and park-detail screens.

// Small risks are real: a 0.3% drought probability must not render as "0%", and
// six parks at 0.9% must not all collapse to an identical "1%". So show one decimal
// below 10% (0.3%, 0.9%, 5.6%) and whole numbers above (54%, 93%).
export const pct = (p) => {
  const v = (p ?? 0) * 100;
  if (v <= 0) return "0%";
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
