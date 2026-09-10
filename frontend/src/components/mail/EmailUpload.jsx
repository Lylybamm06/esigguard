import { Card, CardHeader } from "../ui/Card";
import { Textarea } from "../ui/Input";
import { Button } from "../ui/Button";
import { Badge } from "../ui/Badge";

export default function EmailUpload({
  emailContent,
  setEmailContent,
  isLoading,
  onAnalyze,
  onFileSelected,
  selectedFile,
}) {
  return (
    <Card>
      <CardHeader
        title="Real-time Email Analysis"
        subtitle="Import an .eml file or paste raw content."
        right={
          selectedFile ? (
            <Badge tone="info">{selectedFile.name}</Badge>
          ) : (
            <span className="kbd">Ctrl + Enter</span>
          )
        }
      />

      <Textarea
        label="Email content (optional)"
        placeholder="Paste the email here..."
        value={emailContent}
        onChange={(e) => setEmailContent(e.target.value)}
      />

      <div className="spread" style={{ marginTop: 12 }}>
        <div className="muted">
          {isLoading ? "Uploading & registering analysis..." : "Ready."}
        </div>

        <div className="row">
          <Button variant="primary" onClick={onAnalyze} disabled={isLoading}>
            Analyze
          </Button>

          <label className="btn btn-dark" style={{ cursor: "pointer" }}>
            Import .eml
            <input
              type="file"
              accept=".eml"
              style={{ display: "none" }}
              onChange={(e) => onFileSelected(e.target.files?.[0] || null)}
            />
          </label>

          {selectedFile && (
            <Button
              variant="ghost"
              onClick={() => onFileSelected(null)}
              disabled={isLoading}
            >
              Clear
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
