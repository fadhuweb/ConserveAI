import { Button, Empty } from "antd";

// Runs sensitivity analysis and shows the score CI + how often each intervention is selected.
export default function SensitivityPanel({ result, loading, onRun }) {
  return (
    <div>
      <Button onClick={onRun} loading={loading} style={{ marginBottom: 14 }}>
        Run sensitivity analysis
      </Button>

      {!result ? (
        <Empty description="Tests robustness to ±25% cost/effectiveness error" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <>
          <div className="muted" style={{ fontSize: 13, marginBottom: 12 }}>
            Score {result.score_mean.toFixed(3)} ± {result.score_std.toFixed(3)} ·
            95% CI [{result.score_ci_95[0].toFixed(3)}, {result.score_ci_95[1].toFixed(3)}] ·
            optimal in {result.n_optimal}/{result.n_samples} runs
          </div>
          <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Selection frequency</div>
          {Object.entries(result.selection_freq)
            .sort((a, b) => b[1] - a[1])
            .map(([id, freq]) => (
              <div key={id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                <span style={{ width: 130, fontSize: 12 }} className="muted">{id}</span>
                <div style={{ flex: 1, height: 7, background: "#EEF1F5", borderRadius: 99 }}>
                  <div style={{ height: "100%", borderRadius: 99, width: `${freq * 100}%`,
                    background: freq >= 0.8 ? "#1d6b4f" : "#90A4AE" }} />
                </div>
                <span style={{ width: 36, fontSize: 12, textAlign: "right" }}>{Math.round(freq * 100)}%</span>
              </div>
            ))}
        </>
      )}
    </div>
  );
}
