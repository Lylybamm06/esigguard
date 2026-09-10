import { Card } from "./Card";
import { Badge } from "./Badge";

export function StatCard({ title, value, delta, tone="info" }) {
  return (
    <Card className="stat">
      <div className="spread">
        <div className="muted">{title}</div>
        {delta != null && <Badge tone={tone}>{delta}</Badge>}
      </div>
      <div className="statValue">{value}</div>
    </Card>
  );
}
