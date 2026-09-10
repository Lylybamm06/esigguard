import { useState } from "react";
import { api } from "./api/client";

export default function UploadForm() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const handleUpload = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    const res = await api.post("/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    setResult(res.data);
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Uploader un email</h1>

      <input
        type="file"
        onChange={(e) => setFile(e.target.files[0])}
        style={{ marginTop: "1rem" }}
      />

      <button
        onClick={handleUpload}
        style={{
          marginTop: "1rem",
          padding: "0.5rem 1rem",
          background: "black",
          color: "white",
          borderRadius: "6px",
        }}
      >
        Envoyer
      </button>

      {result && (
        <pre style={{ marginTop: "1rem", background: "#eee", padding: "1rem" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}