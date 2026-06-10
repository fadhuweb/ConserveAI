import { Switch } from "antd";

const TYPES = [
  ["patrol", "Patrol"],
  ["infrastructure", "Infrastructure"],
  ["water", "Water"],
  ["vegetation", "Vegetation"],
  ["community", "Community"],
  ["survey", "Survey"],
];

// Toggle which intervention types the optimiser is allowed to use.
export default function ConstraintControls({ typeEnabled, onChange }) {
  const toggle = (key, val) => onChange({ ...typeEnabled, [key]: val });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 24px" }}>
      {TYPES.map(([key, label]) => (
        <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 14 }}>{label}</span>
          <Switch size="small" checked={typeEnabled[key] !== false} onChange={(v) => toggle(key, v)} />
        </div>
      ))}
    </div>
  );
}
