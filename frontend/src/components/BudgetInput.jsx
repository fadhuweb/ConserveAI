import { Slider, InputNumber } from "antd";

// Budget control: slider + number input, kept in sync. Parent debounces the recommend call.
export default function BudgetInput({ value, onChange, min = 3200000, max = 32000000, step = 800000 }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <span style={{ fontWeight: 600 }}>Budget</span>
        <InputNumber
          value={value}
          min={min}
          max={max}
          step={step}
          formatter={(v) => `₦ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          parser={(v) => v.replace(/₦\s?|(,*)/g, "")}
          onChange={(v) => v != null && onChange(v)}
          style={{ width: 170 }}
        />
      </div>
      <Slider value={value} min={min} max={max} step={step} onChange={onChange}
        tooltip={{ formatter: (v) => `₦${v.toLocaleString()}` }} />
    </div>
  );
}
