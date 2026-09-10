import { useEffect, useState } from "react";
import AppLayout from "../components/layout/AppLayout";
import { Card, CardHeader } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { getStats } from "../api/mail.service";

export default function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    (async () => {
      const data = await getStats();
      setStats(data);
    })();
  }, []);

  const cards = stats?.cards || {};
  const latest = stats?.latest_critical || {};

  return (
    <AppLayout title="Dashboard">
      <div className="grid" style={{ gap: 16 }}>
        <div className="row" style={{ gap: 16, flexWrap: "wrap" }}>
          <Card style={{ minWidth: 260, flex: 1 }}>
            <CardHeader title="Emails analyzed (24h)" subtitle="Uploads in last 24h" />
            <div style={{ fontSize: 42, fontWeight: 800 }}>{cards.emails_24h ?? "-"}</div>
          </Card>

          <Card style={{ minWidth: 260, flex: 1 }}>
            <CardHeader title="Threats detected" subtitle="Risky verdicts (24h)" />
            <div style={{ fontSize: 42, fontWeight: 800 }}>{cards.threats_24h ?? "-"}</div>
          </Card>

          <Card style={{ minWidth: 260, flex: 1 }}>
            <CardHeader title="Blocked" subtitle="Score >= 60 (24h)" />
            <div style={{ fontSize: 42, fontWeight: 800 }}>{cards.blocked_24h ?? "-"}</div>
          </Card>

          <Card style={{ minWidth: 260, flex: 1 }}>
            <CardHeader title="Global risk score" subtitle="Avg score (7 days)" />
            <div style={{ fontSize: 42, fontWeight: 800 }}>
              {cards.global_risk ?? "-"}/100
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader title="Latest critical" subtitle="Highest score (7 days)" right={<Badge tone="good">System OK</Badge>} />
          <div style={{ display: "grid", gap: 10 }}>
            <div className="row" style={{ gap: 10 }}>
              <div className="muted" style={{ width: 120 }}>ID</div>
              <div style={{ fontWeight: 700 }}>{latest.id ?? "-"}</div>
            </div>
            <div className="row" style={{ gap: 10 }}>
              <div className="muted" style={{ width: 120 }}>Verdict</div>
              <div style={{ fontWeight: 700 }}>{latest.final_verdict ?? "-"}</div>
            </div>
            <div className="row" style={{ gap: 10 }}>
              <div className="muted" style={{ width: 120 }}>Score</div>
              <div style={{ fontWeight: 700 }}>{latest.final_score ?? "-"}</div>
            </div>
            <div>
              <div className="muted" style={{ marginBottom: 6 }}>Explanation</div>
              <div className="card" style={{ padding: 14 }}>
                {latest.explanation ? String(latest.explanation) : "-"}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
