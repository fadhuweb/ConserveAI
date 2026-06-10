import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Guards a route. Requires a logged-in user; optionally requires a specific role.
// Enforces the forced password change, and redirects users to their own home
// if they hit a screen outside their role (park-scoping at the route level).
export default function ProtectedRoute({ children, role }) {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;

  if (role && user.role !== role) {
    const home = user.role === "admin" ? "/national" : `/park/${user.park_id}`;
    return <Navigate to={home} replace />;
  }

  return children;
}
