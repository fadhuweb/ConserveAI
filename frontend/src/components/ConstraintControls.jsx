import { Switch } from "antd";

// [type key, label, plain-language description of what it buys]
const TYPES = [
  ["patrol", "Patrols", "Ranger & fire patrol units — anti-poaching and early fire response"],
  ["infrastructure", "Infrastructure", "Fire breaks and physical barriers"],
  ["water", "Water", "Water trucking and borehole / well repair (drought relief)"],
  ["vegetation", "Vegetation", "Revegetation and replanting plots"],
  ["community", "Community", "Community liaison and awareness"],
  ["survey", "Survey", "Aerial / drone monitoring surveys"],
];

// Toggle which intervention types the optimiser is allowed to use.
export default function ConstraintControls({ typeEnabled, onChange }) {
  const toggle = (key, val) => onChange({ ...typeEnabled, [key]: val });

  return (
    <div className="constraints">
      {TYPES.map(([key, label, desc]) => (
        <div key={key} className="constraint-row">
          <div className="constraint-text">
            <div className="constraint-label">{label}</div>
            <div className="constraint-desc">{desc}</div>
          </div>
          <Switch checked={typeEnabled[key] !== false} onChange={(v) => toggle(key, v)} />
        </div>
      ))}
    </div>
  );
}
