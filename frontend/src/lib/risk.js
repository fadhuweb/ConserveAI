// Shared risk-level helpers used by the overview and park-detail screens.

export const pct = (p) => `${Math.round((p ?? 0) * 100)}%`;

export function riskColor(p) {
  if (p >= 0.66) return "#D32F2F"; // high
  if (p >= 0.33) return "#F9A825"; // medium
  return "#43A047";                // low
}

export function riskLabel(p) {
  if (p >= 0.66) return "High";
  if (p >= 0.33) return "Medium";
  return "Low";
}
