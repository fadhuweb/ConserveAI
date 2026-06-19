import { createContext, useContext, useState, useEffect } from "react";
import * as authApi from "../api/auth";

const AuthContext = createContext(null);
const STORAGE_KEY = "conserveai_user";

export function AuthProvider({ children }) {
  // The httpOnly cookie is the real auth; this state just remembers identity
  // for the UI across refreshes.
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : null;
  });

  const persist = (u) => {
    setUser(u);
    if (u) localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    else localStorage.removeItem(STORAGE_KEY);
  };

  // Backfill the full name (login only returns username/role/park) so the
  // sidebar and Settings can show a consistent display name + avatar initials.
  useEffect(() => {
    if (user && user.full_name === undefined) {
      authApi.getMe()
        .then((me) => persist({ ...user, full_name: me.full_name || null }))
        .catch(() => persist({ ...user, full_name: null }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.username]);

  const login = async (username, password) => {
    const data = await authApi.login(username, password);
    const u = {
      username: data.username,
      role: data.role,
      park_id: data.park_id,
      must_change_password: data.must_change_password,
    };
    persist(u);
    return u;
  };

  const logout = async () => {
    try { await authApi.logout(); } catch (_) { /* ignore */ }
    persist(null);
  };

  const clearMustChange = () => {
    if (user) persist({ ...user, must_change_password: false });
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, clearMustChange }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
