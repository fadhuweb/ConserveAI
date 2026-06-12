import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import ChangePassword from "./pages/ChangePassword";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import NationalOverview from "./pages/NationalOverview";
import ParkDetail from "./pages/ParkDetail";
import Managers from "./pages/Managers";

// Sends a logged-in user to their role's home, or to login otherwise.
function Home() {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  return <Navigate to={user.role === "admin" ? "/national" : `/park/${user.park_id}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/change-password" element={<ChangePassword />} />
      <Route
        path="/national"
        element={<ProtectedRoute role="admin"><NationalOverview /></ProtectedRoute>}
      />
      <Route
        path="/managers"
        element={<ProtectedRoute role="admin"><Managers /></ProtectedRoute>}
      />
      <Route
        path="/park/:parkId"
        element={<ProtectedRoute role="manager"><ParkDetail /></ProtectedRoute>}
      />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
