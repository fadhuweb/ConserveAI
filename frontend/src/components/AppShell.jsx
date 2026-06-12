import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  DashboardOutlined, TeamOutlined,
  SettingOutlined, LogoutOutlined, MenuOutlined,
} from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

// Dashboard shell: left sidebar nav + top header bar + content area.
// Wraps the authenticated screens (National Overview, Park Detail).
export default function AppShell({ subtitle, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);   // mobile sidebar toggle

  const cleanName = (user?.username || "?").replace("manager_", "");
  const initials = cleanName.slice(0, 2).toUpperCase();
  const isAdmin = user?.role === "admin";
  const home = isAdmin ? "/national" : `/park/${user?.park_id}`;
  const go = (to) => { navigate(to); setOpen(false); };

  const nav = isAdmin
    ? [
        { label: "National Overview", icon: <DashboardOutlined />, onClick: () => go("/national"), active: pathname === "/national" },
        { label: "Park Managers", icon: <TeamOutlined />, onClick: () => go("/managers"), active: pathname === "/managers" },
        { label: "Settings", icon: <SettingOutlined />, onClick: () => go("/change-password"), active: pathname === "/change-password" },
      ]
    : [
        { label: "My Park", icon: <DashboardOutlined />, onClick: () => go(home), active: pathname === home },
        { label: "Settings", icon: <SettingOutlined />, onClick: () => go("/change-password"), active: pathname === "/change-password" },
      ];

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="sidebar-brand" onClick={() => { navigate(home); setOpen(false); }}>
          <div className="brand-logo">🛡</div>
          <span className="brand-name">ConserveAI</span>
        </div>

        <nav className="sidebar-nav">
          {nav.map((item) => (
            <button key={item.label} className={`nav-item ${item.active ? "active" : ""}`} onClick={item.onClick}>
              {item.icon}<span>{item.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="sidebar-user">
            <div className="avatar">{initials}</div>
            <div className="su-meta">
              <span className="su-name">{cleanName.replace("_", " ")}</span>
              <span className="su-role">{user?.role}</span>
            </div>
          </div>
          <button className="logout-btn full" onClick={logout}><LogoutOutlined /> Log out</button>
        </div>
      </aside>

      {open && <div className="sidebar-scrim" onClick={() => setOpen(false)} />}

      <div className="shell-main">
        <header className="shell-header">
          <button className="hamburger" onClick={() => setOpen(true)}><MenuOutlined /></button>
          <div className="crumb">
            <span className="crumb-top">{isAdmin ? "National Administrator" : "Park Manager"}</span>
            <h1>{subtitle || (isAdmin ? "National Overview" : "Dashboard")}</h1>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
