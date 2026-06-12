import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Row, Col, Spin, Alert, Statistic } from "antd";
import AppShell from "../components/AppShell";
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
import { ngnToUsd } from "../lib/currency";

const THREATS = [["Fire", "fire_prob", "fire"], ["Drought", "drought_prob", "drought"], ["Vegetation", "veg_prob", "vegetation"]];

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
        setZoneWeights(Object.fromEntries(zs.map((z) => [z.id, 1])));   // equal = even split
      })
      .catch(() => setError("Failed to load park data."))
      .finally(() => setLoading(false));
  }, [parkId]);

  // ── recommend (debounced) whenever budget or constraints change ──
  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      setRecommending(true);
      try {
        const res = await recommend({
          park: parkId,
          budget: ngnToUsd(budget),
          type_enabled: typeEnabled,
          zone_weights: zoneWeights,
        });
        if (!cancelled) setRecommendation(res);
      } catch (_) {
        /* keep previous result */
      } finally {
        if (!cancelled) setRecommending(false);
      }
    }, 450);
    return () => { cancelled = true; clearTimeout(t); };
  }, [parkId, budget, typeEnabled, zoneWeights]);

  const latest = forecasts.length ? forecasts[forecasts.length - 1] : null;

  return (
    <AppShell subtitle={meta?.display_name || parkId}>
        {loading ? (
          <div style={{ padding: 100, textAlign: "center" }}><Spin size="large" /></div>
        ) : error ? (
          <Alert type="error" message={error} showIcon />
        ) : (
          <>
            <h2>{meta?.display_name || parkId}</h2>
            <p className="muted" style={{ marginTop: 4 }}>
              {[meta?.state, meta?.ecosystem, meta?.area_km2 && `${meta.area_km2.toLocaleString()} km²`]
                .filter(Boolean).join(" · ")}
            </p>

            {/* current risk */}
            <Row gutter={16} style={{ margin: "16px 0" }}>
              {latest && THREATS.map(([label, key]) => (
                <Col xs={24} sm={8} key={key}>
                  <Card>
                    <Statistic
                      title={`${label} risk (30-day)`}
                      value={pct(latest[key])}
                      valueStyle={{ color: riskColor(latest[key]) }}
                      suffix={<span style={{ fontSize: 13 }}>{riskLabel(latest[key])}</span>}
                    />
                  </Card>
                </Col>
              ))}
            </Row>

            <Card title="Forecast history (last 60 days)" style={{ marginBottom: 16 }}>
              <ForecastChart forecasts={forecasts} />
            </Card>

            <Card title="Forecast drivers" style={{ marginBottom: 16 }}>
              <DriversPanel drivers={drivers?.drivers} />
            </Card>

                <Card title="Budget-constrained recommendation" style={{ marginBottom: 16 }}>
                  <BudgetInput value={budget} onChange={setBudget} />
                  <div style={{ margin: "18px 0" }}>
                    <div style={{ fontWeight: 600, marginBottom: 10 }}>Allowed intervention types</div>
                    <ConstraintControls typeEnabled={typeEnabled} onChange={setTypeEnabled} />
                  </div>

                  <div style={{ margin: "18px 0" }}>
                    <div style={{ fontWeight: 600, marginBottom: 10 }}>Zone priority</div>
                    <ZonePriority zones={zones} weights={zoneWeights} onChange={setZoneWeights} />
                  </div>

                  {recommendation && (
                    <div style={{ display: "flex", gap: 18, flexWrap: "wrap", margin: "8px 0 16px" }}>
                      {THREATS.map(([label, , tkey]) => {
                        const before = recommendation.current_forecast[tkey];
                        const after = recommendation.post_intervention_forecast[tkey];
                        return (
                          <div key={tkey} style={{ fontSize: 13 }}>
                            <div className="muted">{label}</div>
                            <div>
                              <span style={{ color: riskColor(before) }}>{pct(before)}</span>
                              {" → "}
                              <b style={{ color: riskColor(after) }}>{pct(after)}</b>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {recommending
                    ? <div style={{ padding: 20, textAlign: "center" }}><Spin /></div>
                    : <RecommendationsTable recommendation={recommendation} />}
                </Card>

                <Card title="Zone deployment">
                  <ParkMap zones={zones} zoneAllocations={recommendation?.zone_allocations} />
                </Card>
          </>
        )}
    </AppShell>
  );
}
