import { Navigate, useParams } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Guards a route. Requires a logged-in user; optionally requires a specific role.
// Enforces the forced password change, redirects users outside their role to their
// own home, and keeps managers locked to their own park (park-scoping at the route level).
export default function ProtectedRoute({ children, role }) {
  const { user } = useAuth();
  const { parkId } = useParams();

  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;

  if (role && user.role !== role) {
    const home = user.role === "admin" ? "/national" : `/park/${user.park_id}`;
    return <Navigate to={home} replace />;
  }

  // A manager may only open their own park's detail screen.
  if (user.role === "manager" && parkId && parkId !== user.park_id) {
    return <Navigate to={`/park/${user.park_id}`} replace />;
  }

  return children;
}
