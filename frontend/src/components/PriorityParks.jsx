import { riskColor, pct } from "../lib/risk";

const dominantOf = (r) =>
  [["Fire", r.fire_prob], ["Drought", r.drought_prob], ["Vegetation", r.veg_prob]]
    .reduce((a, b) => (b[1] > a[1] ? b : a));

// Parks ranked by overall (highest) risk; click to locate on the map.
export default function PriorityParks({ rows, onLocate }) {
  const ranked = [...rows].sort((a, b) => b.maxRisk - a.maxRisk);

  return (
    <div className="priority-list">
      {ranked.map((r, i) => {
        const dom = dominantOf(r);
        return (
          <div className="priority-item" key={r.park} onClick={() => onLocate(r)}>
            <span className="priority-rank">{i + 1}</span>
            <div className="priority-meta">
              <span className="priority-name">{r.display_name || r.park}</span>
              <span className="priority-dom">{dom[0]} · {pct(dom[1])}</span>
            </div>
            <div className="priority-bar-track">
              <div className="priority-bar" style={{ width: `${Math.round(r.maxRisk * 100)}%`, background: riskColor(r.maxRisk) }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
