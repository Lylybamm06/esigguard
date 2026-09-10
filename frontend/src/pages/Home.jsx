import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import EmailUpload from "../components/EmailUpload";

export default function Home() {
  const [emailContent, setEmailContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleAnalyze = async () => {
    if (!emailContent.trim()) return;

    try {
      setIsLoading(true);

      const blob = new Blob([emailContent], { type: "text/plain" });
      const file = new File([blob], "email.txt", { type: "text/plain" });

      const formData = new FormData();
      formData.append("file", file);

      const res = await api.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const analysisId = res.data.analysis_id;
      if (!analysisId) {
        console.error("Pas d'ID d'analyse dans la réponse :", res.data);
        return;
      }

      navigate(`/result/${analysisId}`);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleImportFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    setEmailContent(text);
  };

  return (
    <main className="app-main">
      <div className="app-container">
        <EmailUpload
          emailContent={emailContent}
          setEmailContent={setEmailContent}
          isLoading={isLoading}
          onAnalyze={handleAnalyze}
          onImportFile={handleImportFile}
        />
      </div>
    </main>
  );
}