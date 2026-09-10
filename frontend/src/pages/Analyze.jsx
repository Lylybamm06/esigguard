import { useState } from "react";
import AppLayout from "../components/layout/AppLayout";
import EmailUpload from "../components/mail/EmailUpload";
import AnalysisSteps from "../components/mail/AnalysisSteps";
import { uploadEmail } from "../api/mail.service";
import { useNavigate } from "react-router-dom";

export default function Analyze() {
  const nav = useNavigate();

  const [emailContent, setEmailContent] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [step, setStep] = useState(0);

  const onFileSelected = async (file) => {
    setSelectedFile(file);

    // preview optionnel
    if (file) {
      const text = await file.text();
      setEmailContent(text);
    }
  };

  const onAnalyze = async () => {
    setIsLoading(true);
    setStep(1);

    try {
      let fileToSend = selectedFile;

      // Si pas de fichier, on crée un .eml depuis la textarea
      if (!fileToSend) {
        const content = emailContent?.trim();
        if (!content) {
          alert("Importe un fichier .eml ou colle un contenu d’email.");
          return;
        }
        const blob = new Blob([content], { type: "message/rfc822" });
        fileToSend = new File([blob], "pasted_email.eml", { type: "message/rfc822" });
      }

      setStep(3);
      const res = await uploadEmail(fileToSend); // POST /api/upload

      // res.analysis_id doit exister si DB insert OK
      nav(`/result/${res.analysis_id}`);
    } catch (e) {
      console.error(e);
      alert("Upload failed. Regarde F12 (Network) + terminal backend.");
    } finally {
      setIsLoading(false);
      setStep(0);
    }
  };

  return (
    <AppLayout title="Analyze email">
      <div className="grid" style={{ gridTemplateColumns: "1.15fr .85fr" }}>
        <EmailUpload
          emailContent={emailContent}
          setEmailContent={setEmailContent}
          isLoading={isLoading}
          onAnalyze={onAnalyze}
          onFileSelected={onFileSelected}
          selectedFile={selectedFile}
        />
        <AnalysisSteps stepIndex={step} />
      </div>
    </AppLayout>
  );
}
