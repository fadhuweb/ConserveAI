import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Skeleton, Alert, Button } from "antd";
import AppShell from "../components/AppShell";
import ParkHeader from "../components/ParkHeader";
import ForecastChart from "../components/ForecastChart";
import DriversPanel from "../components/DriversPanel";
import BudgetInput from "../components/BudgetInput";
import ConstraintControls from "../components/ConstraintControls";
import RecommendationsTable from "../components/RecommendationsTable";
import ParkMap from "../components/ParkMap";
import ZonePriority from "../components/ZonePriority";
import { getPark, getForecasts, getZones, getDrivers } from "../api/forecasts";
import { recommend } from "../api/recommendations";
import { riskColor, riskLabel, pct } from "../lib/risk";
import { ngnToUsd, fmtNGN } from "../lib/currency";

const THREATS = [["Fire", "fire_prob", "fire"], ["Drought", "drought_prob", "drought"], ["Vegetation", "veg_prob", "vegetation"]];

// The three threats and their forecast fields (for the gauges, status alert and
// dominant-threat read). Interventions are decided by the recommender, not hardcoded here.
const GAUGES = [
  ["Fire", "fire_prob"],
  ["Drought", "drought_prob"],
  ["Vegetation", "veg_prob"],
];

// Operational alert — shown ONLY when something needs attention: the dominant
// threat is high, or it has risen notably this week. When the park is calm the
// banner stays hidden, so its presence itself is a signal.
function StatusBanner({ latest, weekAgo }) {
  if (!latest) return null;
  const ranked = [...GAUGES].sort((a, b) => latest[b[1]] - latest[a[1]]);
  const [name, pk] = ranked[0];
  const v = latest[pk];
  const dp = weekAgo ? Math.round((v - weekAgo[pk]) * 100) : 0;

  const high = v >= 0.66;
  const climbing = dp >= 5 && v >= 0.4;
  if (!high && !climbing) return null;

  // State the situation only — the recommender below decides the interventions.
  const cls = high ? "high" : "medium";
  let message;
  if (high) {
    const trend = dp <= -2 ? ", though easing this week" : dp >= 2 ? " and still rising" : "";
    message = <><b>{name} is the top threat</b> at {pct(v)} (high{trend}). Run the planner below to allocate this period's interventions.</>;
  } else {
    message = <><b>{name} risk has climbed {dp} pts this week</b> to {pct(v)}. Plan ahead with the recommender below before it escalates.</>;
  }
  return (
    <div className={`status-banner ${cls}`}>
      <span className="status-dot" />
      <span>{message}</span>
    </div>
  );
}

export default function ParkDetail() {
  const { parkId } = useParams();

  const [meta, setMeta] = useState(null);
  const [forecasts, setForecasts] = useState([]);
  const [zones, setZones] = useState([]);
  const [drivers, setDrivers] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [budget, setBudget] = useState(16000000);   // ₦ (≈ $10,000)
  const [typeEnabled, setTypeEnabled] = useState({});
  const [zoneWeights, setZoneWeights] = useState({});
  const [recommendation, setRecommendation] = useState(null);
  const [recommending, setRecommending] = useState(false);
  const [focus, setFocus] = useState(null);   // "Fire" | "Drought" | "Vegetation" | null
  const toggleFocus = (label) => setFocus((f) => (f === label ? null : label));

  // ── initial load ──
  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      getPark(parkId),
      getForecasts(parkId, 60, "asc"),
      getZones(parkId),
      getDrivers(parkId),
    ])
      .then(([m, fc, zs, dr]) => {
        setMeta(m); setForecasts(fc); setZones(zs); setDrivers(dr);
        setZoneWeights(Object.fromEntries(zs.map((z) => [z.id, 2])));   // Medium = neutral, equal split
      })
      .catch(() => setError("Failed to load park data."))
      .finally(() => setLoading(false));
  }, [parkId]);

  // ── recommend on demand (triggered by the button) ──
  const runRecommend = async () => {
    setRecommending(true);
    try {
      const budgetUsd = ngnToUsd(budget);
      const res = await recommend({
        park: parkId,
        budget: budgetUsd,
        type_enabled: typeEnabled,
        zone_weights: zoneWeights,
      });
      setRecommendation({ ...res, _budgetUsd: budgetUsd });   // remember the budget this ran with
    } catch (_) {
      /* keep previous result */
    } finally {
      setRecommending(false);
    }
  };

  const latest = forecasts.length ? forecasts[forecasts.length - 1] : null;
  // "A week ago" by DATE, not by row position — the forecast series can have gaps
  // (missed daily runs), so counting back 8 rows could land ~2 weeks back and
  // mislabel the delta. Pick the forecast nearest to (latest − 7 days); if none
  // is within 4 days of that mark, we don't have a reliable weekly comparison.
  const weekAgo = (() => {
    if (!latest || forecasts.length < 2) return null;
    const target = new Date(latest.date);
    target.setDate(target.getDate() - 7);
    let best = null, bestDiff = Infinity;
    for (const f of forecasts) {
      if (f === latest) continue;
      const diff = Math.abs(new Date(f.date) - target);
      if (diff < bestDiff) { bestDiff = diff; best = f; }
    }
    return bestDiff <= 4 * 86400000 ? best : null;   // within 4 days of the 7-day mark
  })();
  const deltaFor = (pk) => (latest && weekAgo ? latest[pk] - weekAgo[pk] : null);
  const focusKey = focus ? focus.toLowerCase() : null;   // drivers use lowercase keys

  // Dominant (highest) threat right now — drives the status bar priority.
  const ranked = latest ? GAUGES.map(([l, pk]) => [l, pk, latest[pk]]).sort((a, b) => b[2] - a[2]) : [];
  const dom = ranked[0];

  // Top single move from a recommendation, for the "next action" block.
  const topAlloc = recommendation ? [...(recommendation.allocation || [])].sort((a, b) => b.units - a.units)[0] : null;
  const naBefore = recommendation && dom ? recommendation.current_forecast[dom[0].toLowerCase()] : null;
  const naAfter = recommendation && dom ? recommendation.post_intervention_forecast[dom[0].toLowerCase()] : null;

  return (
    <AppShell subtitle={meta?.display_name || parkId}>
      {loading ? (
        <div>
          <Card style={{ marginBottom: 16 }}><Skeleton active paragraph={{ rows: 2 }} /></Card>
          <Card style={{ marginBottom: 16 }}><Skeleton active paragraph={{ rows: 6 }} /></Card>
          <Card><Skeleton active paragraph={{ rows: 4 }} /></Card>
        </div>
      ) : error ? (
        <Alert type="error" message={error} showIcon />
      ) : (
        <>
          <ParkHeader meta={meta} latest={latest} />

          {/* Compact operational status bar */}
          {latest && (
            <div className="park-statusbar">
              <div className="psb-item">
                <span className="psb-dot" style={{ background: riskColor(dom[2]) }} />
                <span className="psb-label">Priority</span>
                <span className="psb-value">{dom[0]} · {pct(dom[2])}</span>
              </div>
              <div className="psb-sep" />
              <div className="psb-item">
                <span className="psb-label">Planner budget</span>
                <span className="psb-value">{fmtNGN(ngnToUsd(budget))}</span>
              </div>
              <div className="psb-sep" />
              <div className="psb-item">
                <span className="psb-label">Last updated</span>
                <span className="psb-value"
                  title={`Forecast uses data through ${latest.date} (satellite and climate data lag about a day)`}>
                  {latest.computed_at ? String(latest.computed_at).slice(0, 10) : latest.date}
                </span>
              </div>
              <div className="psb-sep" />
              <div className="psb-item">
                <span className="psb-label">Forecast horizon</span>
                <span className="psb-value">30 days</span>
              </div>
            </div>
          )}

          <StatusBanner latest={latest} weekAgo={weekAgo} />

          {/* Current risk snapshot — primary model output */}
          <div className="risk-cards">
            {GAUGES.map(([label, pk]) => {
              const v = latest?.[pk] ?? 0;
              const c = riskColor(v);
              const d = deltaFor(pk);
              const dp = d == null ? null : Math.round(d * 100);
              const dir = dp == null || dp === 0 ? "flat" : dp > 0 ? "up" : "down";
              const active = focus === label;
              const dim = focus && focus !== label;
              return (
                <button key={label} className={`risk-card ${active ? "active" : ""} ${dim ? "dim" : ""}`}
                  onClick={() => toggleFocus(label)} style={active ? { borderColor: c } : undefined}>
                  <div className="rc-top">
                    <span className="rc-label">{label}</span>
                    <span className="rc-level" style={{ color: c }}>{riskLabel(v)}</span>
                  </div>
                  <div className="rc-pct" style={{ color: c }}>{pct(v)}</div>
                  <div className="rc-bar"><div className="rc-fill" style={{ width: pct(v), background: c }} /></div>
                  {dp != null && (
                    <div className={`rc-delta ${dir}`}>
                      {dir === "flat" ? "No change vs last week" : `${dp > 0 ? "▲" : "▼"} ${Math.abs(dp)} pts vs last week`}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Action area: map (left) + deployment plan (right) */}
          <div className="ops-work">
            <Card title="Zone deployment map" className="ops-card park-map-card">
              <ParkMap parkId={parkId} zones={zones} zoneAllocations={recommendation?.zone_allocations} height={460} />
              {recommendation?.zone_allocations?.length > 0 ? (
                <div className="zone-grid">
                  {zones.map((z) => {
                    const items = recommendation.zone_allocations.filter((a) => a.zone_id === z.id);
                    const units = items.reduce((s, a) => s + a.units, 0);
                    const cost = items.reduce((s, a) => s + a.cost, 0);
                    return (
                      <div className="zone-card" key={z.id}>
                        <div className="zone-card-head">
                          <span className="zone-name">{z.name}</span>
                          <span className="zone-total">{units} units · {fmtNGN(cost)}</span>
                        </div>
                        {items.length ? (
                          <div className="zone-items">
                            {items.map((a, i) => (
                              <div className="zone-item" key={i}>
                                <span>{a.intervention_name}</span>
                                <span className="zone-item-units">× {a.units}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="zone-empty">No deployment</div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="muted" style={{ marginTop: 14 }}>
                  Run a recommendation to see which interventions deploy to each zone.
                </p>
              )}
            </Card>

            <Card title="Deployment plan" className="ops-card">
              {recommendation && !recommending && topAlloc && (
                <div className="next-action">
                  <span className="na-icon">▶</span>
                  <div>
                    <div className="na-title">Recommended next action</div>
                    <div className="na-text">
                      Deploy <b>{topAlloc.units}× {topAlloc.name}</b> as your priority.
                      {naBefore != null && naAfter != null && (
                        <> The plan lowers <b>{dom[0]}</b> risk from {pct(naBefore)} to {pct(naAfter)}.</>
                      )}
                    </div>
                  </div>
                </div>
              )}

              <div className="rec-step">
                <div className="rec-step-label">1 · Set your budget</div>
                <BudgetInput value={budget} onChange={setBudget} />
              </div>

              <div className="rec-step">
                <div className="rec-step-label">2 · Allowed intervention types</div>
                <ConstraintControls typeEnabled={typeEnabled} onChange={setTypeEnabled} />
              </div>

              <div className="rec-step">
                <div className="rec-step-label">3 · Zone priority</div>
                <ZonePriority zones={zones} weights={zoneWeights} onChange={setZoneWeights} />
              </div>

              <Button type="primary" size="large" block onClick={runRecommend}
                loading={recommending} style={{ marginTop: 6 }}>
                Recommend interventions
              </Button>

              {recommendation && !recommending && (
                <div className="rec-results">
                  <div className="rec-step-label">Projected impact</div>
                  <div className="rec-impact">
                    {THREATS.map(([label, , tkey]) => {
                      const before = recommendation.current_forecast[tkey];
                      const after = recommendation.post_intervention_forecast[tkey];
                      return (
                        <div key={tkey} className="rec-impact-item">
                          <div className="muted">{label} risk</div>
                          <div className="rec-impact-vals">
                            <span style={{ color: riskColor(before) }}>{pct(before)}</span>
                            <span className="rec-arrow">→</span>
                            <b style={{ color: riskColor(after) }}>{pct(after)}</b>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div className="rec-step-label" style={{ marginTop: 18 }}>Budget utilisation</div>
                  {(() => {
                    const budgetUsd = recommendation._budgetUsd || 0;
                    const spentUsd = recommendation.total_cost || 0;
                    const usedPct = budgetUsd > 0 ? Math.min(100, Math.round((spentUsd / budgetUsd) * 100)) : 0;
                    const remainingUsd = Math.max(0, budgetUsd - spentUsd);
                    const tone = usedPct >= 95 ? "full" : usedPct >= 50 ? "mid" : "low";
                    return (
                      <div className="budget-bar-wrap">
                        <div className="budget-bar-top">
                          <span className="muted">Allocated</span>
                          <span><b>{fmtNGN(spentUsd)}</b> of {fmtNGN(budgetUsd)} · {usedPct}%</span>
                        </div>
                        <div className="budget-track">
                          <div className={`budget-fill ${tone}`} style={{ width: `${usedPct}%` }} />
                        </div>
                        <div className="budget-sub muted">
                          {usedPct >= 95 ? "Budget fully allocated." : `${fmtNGN(remainingUsd)} left unspent.`}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              )}
            </Card>
          </div>

          {/* ── Supporting evidence — why the model says this ── */}
          <Card title={`Forecast history${focus ? ` — ${focus}` : " (last 60 days)"}`} style={{ marginBottom: 16 }}>
            <ForecastChart forecasts={forecasts} focus={focus} />
          </Card>

          <Card title={`Forecast drivers${focus ? ` — ${focus}` : ""}`} style={{ marginBottom: 16 }}>
            <DriversPanel drivers={drivers?.drivers} focus={focusKey} />
          </Card>

          {recommendation && !recommending && (
            <Card title="Recommended interventions">
              <RecommendationsTable recommendation={recommendation} />
            </Card>
          )}
        </>
      )}
    </AppShell>
  );
}
