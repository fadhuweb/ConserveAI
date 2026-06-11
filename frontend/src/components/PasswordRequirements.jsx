import { CheckCircleFilled, CloseCircleOutlined } from "@ant-design/icons";

// Keep these in sync with the backend PASSWORD_RULES.
export const RULES = [
  { label: "At least 8 characters", test: (p) => p.length >= 8 },
  { label: "An uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "A lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "A number", test: (p) => /\d/.test(p) },
  { label: "A special character", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

export const passwordValid = (p) => RULES.every((r) => r.test(p || ""));

export default function PasswordRequirements({ value }) {
  const p = value || "";
  return (
    <ul className="pw-reqs">
      {RULES.map((r) => {
        const ok = r.test(p);
        return (
          <li key={r.label} style={{ color: ok ? "#43A047" : "var(--muted)" }}>
            {ok ? <CheckCircleFilled /> : <CloseCircleOutlined />} {r.label}
          </li>
        );
      })}
    </ul>
  );
}
