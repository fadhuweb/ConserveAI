import { pct } from "../lib/risk";

// Ecosystem-themed banner for the park detail page.
const ECO = {
  savanna:    "linear-gradient(135deg, #0f766e 0%, #115e59 100%)",
  rainforest: "linear-gradient(135deg, #064e3b 0%, #047857 100%)",
  sahel:      "linear-gradient(135deg, #78350f 0%, #b45309 100%)",
  mixed:      "linear-gradient(135deg, #022c22 0%, #065f46 100%)",
};

// faint topographic contour lines for depth
const Contour = () => (
  <svg className="ph-contour" viewBox="0 0 600 220" preserveAspectRatio="none" aria-hidden="true">
    <g fill="none" stroke="#ffffff" strokeWidth="2">
      <path d="M-20 60 C 120 20, 220 120, 360 70 C 480 30, 560 110, 640 70" opacity="0.12" />
      <path d="M-20 110 C 130 70, 230 170, 370 120 C 490 80, 570 160, 640 120" opacity="0.16" />
      <path d="M-20 160 C 140 120, 240 220, 380 170 C 500 130, 580 210, 640 170" opacity="0.10" />
    </g>
  </svg>
);

export default function ParkHeader({ meta, latest }) {
  if (!meta) return null;
  const grad = ECO[(meta.ecosystem || "").toLowerCase()] || ECO.mixed;

  const threats = latest
    ? [["Fire", latest.fire_prob], ["Drought", latest.drought_prob], ["Vegetation", latest.veg_prob]]
    : [];
  const top = threats.length ? threats.reduce((a, b) => (b[1] > a[1] ? b : a)) : null;

  return (
    <div className="park-header" style={{ background: grad }}>
      <Contour />
      <div className="ph-main">
        <div className="ph-eyebrow">National Park</div>
        <h1 className="ph-title">{meta.display_name}</h1>
        <div className="ph-badges">
          {meta.state && <span className="ph-badge">{meta.state}</span>}
          {meta.ecosystem && <span className="ph-badge" style={{ textTransform: "capitalize" }}>{meta.ecosystem}</span>}
          {meta.area_km2 && <span className="ph-badge">{meta.area_km2.toLocaleString()} km²</span>}
        </div>
      </div>
      {top && (
        <div className="ph-status">
          <div className="ph-status-label">Highest threat</div>
          <div className="ph-status-val">{top[0]}</div>
          <div className="ph-status-pct">{pct(top[1])}</div>
        </div>
      )}
    </div>
  );
}
