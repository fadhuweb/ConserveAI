import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Tooltip } from "antd";
import {
  DashboardOutlined, TeamOutlined, AppstoreOutlined,
  SettingOutlined, LogoutOutlined, MenuOutlined,
  MenuFoldOutlined, MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useAuth } from "../auth/AuthContext";

// Dashboard shell: left sidebar nav + top header bar + content area.
// Wraps the authenticated screens (National Overview, Park Detail).
export default function AppShell({ subtitle, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);   // mobile drawer
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("sidebar_collapsed") === "1");

  const toggleSidebar = () => {
    if (typeof window !== "undefined" && window.innerWidth < 900) {
      setOpen((o) => !o);                       // mobile: open/close drawer
    } else {
      setCollapsed((c) => {                     // desktop: collapse to icon rail
        localStorage.setItem("sidebar_collapsed", c ? "0" : "1");
        return !c;
      });
    }
  };

  const cleanName = (user?.username || "?").replace("manager_", "");
  const initials = cleanName.slice(0, 2).toUpperCase();
  const isAdmin = user?.role === "admin";
  const home = isAdmin ? "/national" : `/park/${user?.park_id}`;
  const go = (to) => { navigate(to); setOpen(false); };

  const nav = isAdmin
    ? [
        { label: "National Overview", icon: <DashboardOutlined />, onClick: () => go("/national"), active: pathname === "/national" },
        { label: "Park Managers", icon: <TeamOutlined />, onClick: () => go("/managers"), active: pathname === "/managers" },
        { label: "Interventions", icon: <AppstoreOutlined />, onClick: () => go("/interventions"), active: pathname === "/interventions" },
        { label: "Settings", icon: <SettingOutlined />, onClick: () => go("/settings"), active: pathname === "/settings" },
      ]
    : [
        { label: "My Park", icon: <DashboardOutlined />, onClick: () => go(home), active: pathname === home },
        { label: "Interventions", icon: <AppstoreOutlined />, onClick: () => go("/interventions"), active: pathname === "/interventions" },
        { label: "Settings", icon: <SettingOutlined />, onClick: () => go("/settings"), active: pathname === "/settings" },
      ];

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "open" : ""} ${collapsed ? "collapsed" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-id" onClick={() => { navigate(home); setOpen(false); }}>
            <div className="brand-logo">🛡</div>
            <span className="brand-name">ConserveAI</span>
          </div>
          <button className="brand-collapse" onClick={toggleSidebar}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </button>
        </div>

        <nav className="sidebar-nav">
          <div className="nav-section">Menu</div>
          {nav.map((item) => (
            <Tooltip key={item.label} title={collapsed ? item.label : null} placement="right">
              <button className={`nav-item ${item.active ? "active" : ""}`} onClick={item.onClick}>
                {item.icon}<span>{item.label}</span>
              </button>
            </Tooltip>
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
          <Tooltip title={collapsed ? "Log out" : null} placement="right">
            <button className="logout-btn full" onClick={logout}><LogoutOutlined /> <span>Log out</span></button>
          </Tooltip>
        </div>
      </aside>

      {open && <div className="sidebar-scrim" onClick={() => setOpen(false)} />}

      <div className="shell-main">
        <header className="shell-header">
          <button className="hamburger" onClick={toggleSidebar} title="Toggle sidebar"><MenuOutlined /></button>
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
