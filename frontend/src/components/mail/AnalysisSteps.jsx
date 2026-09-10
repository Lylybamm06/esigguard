import { Card, CardHeader } from "../ui/Card";
import { Progress } from "../ui/Progress";
import { Badge } from "../ui/Badge";

const steps = [
  "Syntax parsing",
  "Header checks (SPF/DKIM)",
  "Link extraction",
  "Semantic intent scoring",
  "Final verdict",
];

export default function AnalysisSteps({ stepIndex=0 }) {
  const pct = Math.round(((stepIndex+1) / steps.length) * 100);
  return (
    <Card>
      <CardHeader
        title="Analysis pipeline"
        subtitle="Transparent steps for explainability."
        right={<Badge tone="info">{pct}%</Badge>}
      />
      <Progress value={pct} />
      <div className="grid" style={{marginTop:12, gap:10}}>
        {steps.map((s, idx) => (
          <div key={s} className="spread" style={{padding:"10px 12px", border:"1px solid var(--stroke)", borderRadius:14, background:"rgba(0,0,0,.12)"}}>
            <div style={{fontSize:13}}>{s}</div>
            <span className="muted">
              {idx < stepIndex ? "Done" : idx === stepIndex ? "Running" : "Pending"}
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}
