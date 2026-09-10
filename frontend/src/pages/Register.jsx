import { useMemo, useState } from "react";
import { Card, CardHeader } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import { Button } from "../components/ui/Button";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { saveSession } from "../auth/session";

export default function Register() {
  const nav = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const passwordsMatch = useMemo(() => password.length > 0 && password === confirm, [password, confirm]);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");

    if (!passwordsMatch) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/api/auth/register", {
        username: username.trim(),
        email: email.trim(),
        password,
      });

      // Option: auto-login après register
      const res = await api.post("/api/auth/login", {
        username: email.trim() || username.trim(),
        password,
      });

      const payload = res?.data || {};
      saveSession(
        {
          username: payload.username ?? username.trim(),
          email: payload.email ?? email.trim(),
          access_token: payload.access_token,
          loggedAt: new Date().toISOString(),
        },
        true
      );

      nav("/dashboard");
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Inscription impossible. Vérifie que l'API tourne et que l'utilisateur n'existe pas déjà.";
      setError(String(msg));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="authWrap">
      <div className="authLeft">
        <h1>Create your account</h1>
        <p className="muted">Build a personal security dashboard and analysis history.</p>
        <div className="authChecks">
          <div className="muted">✔ Explainable scoring</div>
          <div className="muted">✔ Private history</div>
          <div className="muted">✔ Secure defaults</div>
        </div>
      </div>

      <Card className="authCard">
        <CardHeader title="Registration" subtitle="Use a professional email for best deliverability checks." />
        <form className="grid" style={{ gap: 12 }} onSubmit={onSubmit}>
          <Input
            label="Username"
            placeholder="marylyne"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <Input label="Email" placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              hint="Use 12+ characters."
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Input
              label="Confirm password"
              type="password"
              placeholder="••••••••"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>

          {error ? (
            <div className="badge badge-warn" style={{ justifySelf: "start" }}>
              {error}
            </div>
          ) : null}

          <Button type="submit" disabled={loading || !username.trim() || !email.trim() || !password || !confirm}>
            {loading ? "Creating..." : "Create account"}
          </Button>

          <div className="muted" style={{ textAlign: "center" }}>
            Already registered?{" "}
            <Link to="/login" style={{ color: "var(--info)" }}>
              Login
            </Link>
          </div>
        </form>
      </Card>
    </div>
  );
}
