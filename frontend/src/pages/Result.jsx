import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import AppLayout from "../components/layout/AppLayout";
import { Card, CardHeader } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { getAnalysisById } from "../api/mail.service";

function toneFromVerdict(v) {
  if (!v) return "neutral";
  const x = String(v).toLowerCase();
  if (x.includes("danger") || x.includes("critical") || x.includes("phish")) return "bad";
  if (x.includes("sus")) return "warn";
  return "good";
}

function toneFromStatus(s) {
  const x = String(s || "").toLowerCase();
  if (x.includes("pending") || x.includes("processing")) return "warn";
  if (x.includes("done")) return "good";
  return "neutral";
}

export default function Result() {
  const { id } = useParams();
  const nav = useNavigate();

  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    (async () => {
      try {
        setErr("");
        setLoading(true);
        const data = await getAnalysisById(id);
        setAnalysis(data);
      } catch (e) {
        // axios error
        const msg =
          e?.response?.data?.detail ||
          e?.response?.data?.error ||
          e?.message ||
          "Failed to load analysis";
        setErr(String(msg));
        setAnalysis(null);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  return (
    <AppLayout title="Analysis details">
      <Card>
        <CardHeader
          title="Analysis details"
          subtitle="Explainable scoring"
          right={<span className="kbd">ID {id}</span>}
        />

        {loading && <div className="muted">Loading…</div>}

        {!loading && err && (
          <div style={{ display: "grid", gap: 12 }}>
            <div className="muted">Analysis not found.</div>
            <div className="row">
              <Button onClick={() => nav("/history")}>Back to history</Button>
            </div>
            <div className="muted" style={{ fontSize: 12 }}>
              Debug: {err}
            </div>
          </div>
        )}

        {!loading && !err && analysis && (
          <div style={{ display: "grid", gap: 14 }}>
            <div className="spread">
              <div style={{ display: "grid", gap: 8 }}>
                <div className="row" style={{ gap: 10 }}>
                  <div style={{ width: 120 }} className="muted">
                    Status
                  </div>
                  <Badge tone={toneFromStatus(analysis.status)}>{analysis.status || "-"}</Badge>
                </div>

                <div className="row" style={{ gap: 10 }}>
                  <div style={{ width: 120 }} className="muted">
                    Final verdict
                  </div>
                  <Badge tone={toneFromVerdict(analysis.final_verdict)}>
                    {analysis.final_verdict || "-"}
                  </Badge>
                </div>

                <div className="row" style={{ gap: 10 }}>
                  <div style={{ width: 120 }} className="muted">
                    Final score
                  </div>
                  <div style={{ fontWeight: 700 }}>{analysis.final_score ?? "-"}</div>
                </div>
              </div>

              <div className="row">
                <Button onClick={() => nav("/history")}>Back</Button>
              </div>
            </div>

            <div style={{ borderTop: "1px solid rgba(255,255,255,.06)", paddingTop: 14 }}>
              <div className="muted" style={{ marginBottom: 8 }}>
                Explanation
              </div>
              <div className="card" style={{ padding: 14 }}>
                {analysis.human_explanation ? String(analysis.human_explanation) : "-"}
              </div>
            </div>
          </div>
        )}
      </Card>
    </AppLayout>
  );
}
