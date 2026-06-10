import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Shared application header used on every authenticated screen.
export default function TopBar({ subtitle }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  // Get clean initials for the avatar (e.g. "YA" for manager_yankari, "AD" for admin)
  const cleanName = (user?.username || "?").replace("manager_", "");
  const initials = cleanName.slice(0, 2).toUpperCase();

  return (
    <header className="topbar">
      <div className="brand" onClick={() => navigate("/")} style={{ cursor: "pointer" }}>
        <div className="brand-logo">🛡</div>
        <span className="brand-name">ConserveAI</span>
        {subtitle && <span className="brand-sub">{subtitle}</span>}
      </div>
      <div className="user">
        <div className="avatar" title={user?.username}>{initials}</div>
        <span className="uname" style={{ textTransform: "capitalize" }}>
          {cleanName.replace("_", " ")}
        </span>
        <button className="logout-btn" onClick={logout}>Log out</button>
      </div>
    </header>
  );
}
