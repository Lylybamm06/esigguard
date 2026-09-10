import { Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import Result from "./pages/Result";
import { isLoggedIn } from "./auth/session";

function RequireAuth({ children }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/analyze" element={<RequireAuth><Analyze /></RequireAuth>} />
      <Route path="/history" element={<RequireAuth><History /></RequireAuth>} />
      <Route path="/result/:id" element={<RequireAuth><Result /></RequireAuth>} />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
