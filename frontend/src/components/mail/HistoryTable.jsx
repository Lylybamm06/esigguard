import { Table } from "../ui/Table";
import { Badge } from "../ui/Badge";

function toneFromVerdict(v) {
  if (!v) return "neutral";
  const x = String(v).toLowerCase();
  if (x.includes("danger") || x.includes("critical") || x.includes("phish")) return "bad";
  if (x.includes("sus")) return "warn";
  return "good";
}

function toneFromStatus(s) {
  const x = String(s || "").toLowerCase();
  if (x.includes("pending")) return "warn";
  if (x.includes("processing")) return "warn";
  if (x.includes("done")) return "good";
  return "neutral";
}

export default function HistoryTable({ rows, onOpen }) {
  const columns = [
    { key: "id", header: "ID" },
    {
      key: "upload_date",
      header: "Date",
      render: (r) => (r.upload_date ? String(r.upload_date) : "-"),
    },
    {
      key: "status",
      header: "Status",
      render: (r) => <Badge tone={toneFromStatus(r.status)}>{r.status || "-"}</Badge>,
    },
    {
      key: "final_verdict",
      header: "Verdict",
      render: (r) => <Badge tone={toneFromVerdict(r.final_verdict)}>{r.final_verdict || "-"}</Badge>,
    },
    {
      key: "final_score",
      header: "Score",
      render: (r) => (r.final_score ?? "-"),
    },
  ];

  return <Table columns={columns} rows={rows} onRowClick={onOpen} />;
}
