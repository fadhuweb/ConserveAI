import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import * as authApi from "../api/auth";

export default function ChangePassword() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await authApi.changePassword(current, next);
      // Backend clears the cookie and requires a fresh login with the new password.
      setDone(true);
      await logout();
      setTimeout(() => navigate("/login"), 1500);
    } catch (err) {
      const detail = err?.response?.data?.detail || "Could not change password";
      setError(detail);
    }
  };

  if (done) {
    return (
      <div className="login-wrap">
        <div className="login-box">
          <h2>Password changed</h2>
          <p className="muted">Please log in again with your new password…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="login-wrap">
      <form className="login-box" onSubmit={submit}>
        <h2>Set your password</h2>
        <p className="muted">
          {user?.username}: you must set a new password on first login.
        </p>

        <label>Current (temporary) password</label>
        <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoFocus />

        <label>New password (min 8 characters)</label>
        <input type="password" value={next} onChange={(e) => setNext(e.target.value)} />

        {error && <div className="error">{error}</div>}

        <button className="btn">Change password</button>
      </form>
    </div>
  );
}
