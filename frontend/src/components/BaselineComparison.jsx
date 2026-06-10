// Compares the ILP plan's total risk-reduction score against naive baselines.
export default function BaselineComparison({ baselines }) {
  if (!baselines || baselines.length === 0) return null;

  const max = Math.max(...baselines.map((b) => b.total_score), 0.0001);

  return (
    <div>
      {baselines.map((b) => {
        const isIlp = b.strategy.startsWith("ILP");
        return (
          <div key={b.strategy} style={{ marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 4 }}>
              <span style={{ fontWeight: isIlp ? 700 : 500 }}>{b.strategy}</span>
              <span className="muted">score {b.total_score.toFixed(3)}</span>
            </div>
            <div style={{ height: 8, background: "#EEF1F5", borderRadius: 99 }}>
              <div style={{ height: "100%", borderRadius: 99,
                width: `${(b.total_score / max) * 100}%`,
                background: isIlp ? "#1d6b4f" : "#B0BEC5" }} />
            </div>
          </div>
        );
      })}
      <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
        Higher score = more total risk reduced for the budget.
      </p>
    </div>
  );
}
