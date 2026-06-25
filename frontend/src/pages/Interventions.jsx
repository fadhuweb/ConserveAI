import { useEffect, useState } from "react";
import { Tag, Spin, Alert } from "antd";
import AppShell from "../components/AppShell";
import { getCatalog } from "../api/forecasts";

const TYPE_LABEL = {
  patrol: "Patrol", infrastructure: "Infrastructure", water: "Water",
  vegetation: "Vegetation", community: "Community", survey: "Survey",
};
// Plain-language explanation of each intervention and why it matters.
const DESCRIPTIONS = {
  fire_patrol:   "Ground patrol teams that spot and respond to fire outbreaks early, before they spread.",
  ranger:        "Rangers deployed across a zone to deter poaching and give first response to fire and other threats.",
  fire_break:    "Cleared strips of land that stop wildfire from spreading between areas of vegetation.",
  water_truck:   "Trucked-in water to top up waterholes and relieve drought stress in dry zones.",
  borehole:      "Repairing or drilling boreholes and wells for a reliable dry-season water supply.",
  revegetation:  "Replanting degraded plots to restore vegetation cover and slow land degradation.",
  community:     "Engagement and awareness work with neighbouring communities to reduce human-caused fire and poaching.",
  aerial_survey: "Aerial or drone surveys that monitor fire, vegetation and wildlife across hard-to-reach terrain.",
};
const THREATS = [
  ["effectiveness_fire", "Fire", "#E64A19"],
  ["effectiveness_drought", "Drought", "#1976D2"],
  ["effectiveness_veg", "Vegetation", "#388E3C"],
];
const MAX_EFF = 0.30; // bars scaled to the catalog's strongest per-unit effect

export default function Interventions() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getCatalog()
      .then(setItems)
      .catch(() => setError("Failed to load the intervention catalog."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppShell subtitle="Interventions">
      <h2>Intervention catalog</h2>
      <p className="muted" style={{ marginTop: 4, marginBottom: 20, fontSize: 15 }}>
        The conservation actions the recommender can deploy. The bars show the expected risk
        reduction per unit for each threat over a 30-day plan.
      </p>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      {loading ? (
        <div style={{ padding: 60, textAlign: "center" }}><Spin size="large" /></div>
      ) : (
        <div className="catalog-grid">
          {items.map((iv) => (
            <div className="catalog-card" key={iv.id}>
              <div className="cat-head">
                <span className="cat-name">{iv.name}</span>
                <Tag>{TYPE_LABEL[iv.type] || iv.type}</Tag>
              </div>
              {DESCRIPTIONS[iv.id] && <p className="cat-desc">{DESCRIPTIONS[iv.id]}</p>}
              <div className="cat-meta">
                <span className="muted">Up to {iv.max_units} units per plan</span>
              </div>
              <div className="cat-eff">
                {THREATS.map(([k, label, color]) => {
                  const v = iv[k] || 0;
                  return (
                    <div className="eff-row" key={k}>
                      <span className="eff-label">{label}</span>
                      <div className="eff-track">
                        <div className="eff-bar" style={{ width: `${Math.min(100, (v / MAX_EFF) * 100)}%`, background: color }} />
                      </div>
                      <span className="eff-val">{Math.round(v * 100)}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </AppShell>
  );
}
