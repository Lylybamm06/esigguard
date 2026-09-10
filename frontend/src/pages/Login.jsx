import { useState } from "react";
import { Card, CardHeader } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { saveSession } from "../auth/session";

export default function Login() {
  const nav = useNavigate();

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await api.post("/api/auth/login", {
        // le backend accepte username OU email (même champ)
        username: identifier.trim(),
        password,
      });

      const payload = res?.data || {};
      const session = {
        username: payload.username ?? identifier.trim(),
        email: payload.email ?? null,
        access_token: payload.access_token,
        loggedAt: new Date().toISOString(),
      };

      saveSession(session, remember);

      nav("/dashboard");
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Connexion impossible. Vérifie tes identifiants et que l'API tourne.";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="authWrap">
      <div className="authLeft">
        <h1>ESIG’GUARD</h1>
        <p className="muted">Professional email threat analysis platform.</p>
        <div className="authPills">
          <span className="badge badge-info">AI Scoring</span>
          <span className="badge badge-good">SOC Workflow</span>
          <span className="badge badge-warn">Explainable</span>
        </div>
      </div>

      <Card className="authCard">
        <CardHeader title="Secure Login" subtitle="Access is monitored and attempts are rate-limited." />
        <form className="grid" style={{ gap: 12 }} onSubmit={onSubmit}>
          <Input
            label="Username or Email"
            placeholder="marylyne | mary@example.com"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
          />
          <Input
            label="Password"
            placeholder="••••••••"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {error ? (
            <div className="badge badge-warn" style={{ justifySelf: "start" }}>
              {error}
            </div>
          ) : null}

          <div className="spread">
            <label className="muted" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Remember me
            </label>
            <span className="muted">Forgot password?</span>
          </div>

          <Button type="submit" disabled={loading || !identifier.trim() || !password}>
            {loading ? "Logging in..." : "Login"}
          </Button>

          <div className="muted" style={{ textAlign: "center" }}>
            No account?{" "}
            <Link to="/register" style={{ color: "var(--info)" }}>
              Create one
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
}
