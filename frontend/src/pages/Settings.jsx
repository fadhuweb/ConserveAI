import { useEffect, useState } from "react";
import { Card, Tag, Skeleton, Alert } from "antd";
import {
  PhoneOutlined, IdcardOutlined, EnvironmentOutlined,
} from "@ant-design/icons";
import AppShell from "../components/AppShell";
import * as authApi from "../api/auth";
import { getParks } from "../api/forecasts";

export default function Settings() {
  const [me, setMe] = useState(null);
  const [parks, setParks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([authApi.getMe(), getParks()])
      .then(([u, p]) => { setMe(u); setParks(p); })
      .catch(() => setError("Could not load your account."))
      .finally(() => setLoading(false));
  }, []);

  const parkName = (id) => parks.find((p) => p.id === id)?.display_name || id;
  const isAdmin = me?.role === "admin";
  const display = me?.full_name || me?.username || "";
  const initials = display.replace(/[^a-zA-Z ]/g, "").split(" ").filter(Boolean)
    .slice(0, 2).map((s) => s[0]).join("").toUpperCase() || "?";

  // Name, role and email live in the hero above — the tiles show the rest, so
  // nothing is duplicated and the three fill one clean row.
  const fields = [
    { icon: <IdcardOutlined />, label: "Username", value: me?.username },
    { icon: <PhoneOutlined />, label: "Phone", value: me?.phone },
    { icon: <EnvironmentOutlined />, label: "Assigned park",
      value: me?.park_id ? parkName(me.park_id) : "All parks (national)" },
  ];

  return (
    <AppShell subtitle="Settings">
      <h2 style={{ marginTop: 0 }}>Settings</h2>

      {/* Profile hero */}
      <div className={`settings-hero ${isAdmin ? "admin" : "manager"}`}>
        {loading ? (
          <Skeleton avatar active title paragraph={{ rows: 1 }} />
        ) : (
          <>
            <div className="settings-avatar">{initials}</div>
            <div className="settings-hero-meta">
              <div className="settings-hero-name">{display}</div>
              <div className="settings-hero-sub">
                <Tag color={isAdmin ? "gold" : "green"} style={{ marginInlineEnd: 8 }}>
                  {isAdmin ? "National administrator" : "Park manager"}
                </Tag>
                {me?.email && <span className="muted">{me.email}</span>}
              </div>
            </div>
          </>
        )}
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ maxWidth: 980, marginBottom: 16 }} />}

      <Card title="Account details" style={{ maxWidth: 980 }}>
        {loading ? (
          <Skeleton active paragraph={{ rows: 4 }} />
        ) : (
          <div className="settings-tiles">
            {fields.map((f) => (
              <div className="settings-tile" key={f.label}>
                <span className="st-icon">{f.icon}</span>
                <div className="st-text">
                  <div className="st-label">{f.label}</div>
                  <div className="st-value">{f.value || <span className="muted">—</span>}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </AppShell>
  );
}
