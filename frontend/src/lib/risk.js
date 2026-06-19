// Shared risk-level helpers used by the overview and park-detail screens.

export const pct = (p) => `${Math.round((p ?? 0) * 100)}%`;

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
