import { useNavigate } from "react-router-dom";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { clearSession, getSession } from "../../auth/session";

export default function Topbar({ title, right }) {
  const nav = useNavigate();
  const session = getSession();

  function logout() {
    clearSession();
    nav("/login", { replace: true });
  }

  return (
    <div className="topbar">
      <div>
        <div className="topTitle">{title}</div>
        <div className="topSub">
          {session?.username ? `Connecté : ${session.username}` : "Non connecté"} · Role: Analyst
        </div>
      </div>
      <div className="row">
        <Badge tone="info">System OK</Badge>
        {right}
        <Button variant="ghost" onClick={logout}>
          Déconnexion
        </Button>
      </div>
    </div>
  );
}
