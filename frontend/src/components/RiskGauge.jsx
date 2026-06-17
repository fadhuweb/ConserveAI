import { Tooltip } from "antd";
import { riskColor, riskLabel } from "../lib/risk";

// Radial gauge tile for a single threat probability (0–1).
// `delta` is the change vs ~a week ago (fraction); `active`/`dim` drive the
// click-to-focus state; `onClick` toggles focus on this threat.
export default function RiskGauge({ label, value, delta, active, dim, onClick }) {
  const v = value ?? 0;
  const pct = Math.round(v * 100);
  const color = riskColor(v);
  const R = 54;
  const C = 2 * Math.PI * R;
  const offset = C * (1 - v);
  const gid = `gauge-${label}`;

  const dp = delta == null ? null : Math.round(delta * 100);
  const dir = dp == null || dp === 0 ? "flat" : dp > 0 ? "up" : "down";

  const cls = ["gauge-tile", onClick ? "clickable" : "", active ? "active" : "", dim ? "dim" : ""]
    .filter(Boolean).join(" ");

  return (
    <div className={cls} onClick={onClick} role={onClick ? "button" : undefined}
         style={active ? { borderColor: color } : undefined}>
      <div className="gauge-head">{label} risk</div>
      <svg width="150" height="150" viewBox="0 0 150 150">
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.78" />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
        </defs>
        <circle cx="75" cy="75" r={R} fill="none" stroke="#EDF1F5" strokeWidth="13" />
        <circle
          cx="75" cy="75" r={R} fill="none" stroke={`url(#${gid})`} strokeWidth="13"
          strokeLinecap="round" strokeDasharray={C} strokeDashoffset={offset}
          transform="rotate(-90 75 75)" className="gauge-arc"
          style={{ filter: `drop-shadow(0 2px 5px ${color}55)` }}
        />
        <text x="75" y="71" textAnchor="middle" className="gauge-pct" fill={color}>{pct}<tspan fontSize="16" dy="-2">%</tspan></text>
        <text x="75" y="95" textAnchor="middle" className="gauge-level">{riskLabel(v)}</text>
      </svg>
      {dp != null && (
        <Tooltip title="Change in this threat's risk versus about a week ago, in percentage points (e.g. 45% → 50% is +5 pts).">
          <div className={`gauge-delta ${dir}`}>
            {dir === "flat"
              ? "No change vs last week"
              : `${dp > 0 ? "▲" : "▼"} ${Math.abs(dp)} pts vs last week`}
          </div>
        </Tooltip>
      )}
    </div>
  );
}
