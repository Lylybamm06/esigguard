import { useEffect, useMemo, useState } from "react";
import AppLayout from "../components/layout/AppLayout";
import { Card, CardHeader } from "../components/ui/Card";
import { Input } from "../components/ui/Input";
import HistoryTable from "../components/mail/HistoryTable";
import { getAnalyses } from "../api/mail.service";
import { useNavigate } from "react-router-dom";

export default function History() {
  const nav = useNavigate();
  const [rows, setRows] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    (async () => {
      const data = await getAnalyses();
      setRows(data);
    })();
  }, []);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return rows;
    return rows.filter((r) => {
      return (
        String(r.id ?? "").includes(s) ||
        String(r.final_verdict ?? "").toLowerCase().includes(s) ||
        String(r.status ?? "").toLowerCase().includes(s) ||
        String(r.final_score ?? "").includes(s)
      );
    });
  }, [rows, q]);

  return (
    <AppLayout title="History">
      <Card>
        <CardHeader
          title="Audit log"
          subtitle="Click a row to open the detailed result."
          right={
            <Input
              placeholder="Search (id, verdict, status, score...)"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          }
        />

        <HistoryTable rows={filtered} onOpen={(r) => nav(`/result/${r.id}`)} />
      </Card>
    </AppLayout>
  );
}
