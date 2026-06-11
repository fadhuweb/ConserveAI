import { Select } from "antd";

// Manager assigns a priority to each zone. Higher priority → more units allocated
// there (feeds the backend's zone_weights). All-equal reduces to an even split.
const LEVELS = [
  { label: "Low", value: 1 },
  { label: "Medium", value: 2 },
  { label: "High", value: 3 },
  { label: "Critical", value: 4 },
];

export default function ZonePriority({ zones, weights, onChange }) {
  const set = (id, w) => onChange({ ...weights, [id]: w });

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "10px 24px" }}>
      {zones.map((z) => (
        <div key={z.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 14 }}>{z.name}</span>
          <Select
            size="small"
            value={weights[z.id] || 1}
            onChange={(w) => set(z.id, w)}
            options={LEVELS}
            style={{ width: 120 }}
          />
        </div>
      ))}
    </div>
  );
}
