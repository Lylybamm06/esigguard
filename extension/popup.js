async function getEmailFromGmailTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const response = await chrome.tabs.sendMessage(tab.id, { type: "GET_EMAIL" });
  if (!response || !response.ok) throw new Error("Impossible de lire l'email (ouvrez un mail dans Gmail).");
  return response.data;
}

async function callApi(payload) {
  const res = await fetch("http://127.0.0.1:8000/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("API error: " + res.status);
  return await res.json();
}

document.getElementById("analyzeBtn").addEventListener("click", async () => {
  const resultDiv = document.getElementById("result");
  resultDiv.textContent = "Analyse en cours...";

  try {
    const email = await getEmailFromGmailTab();

    const apiResponse = await callApi({
      sender: email.sender,
      subject: email.subject,
      body: email.body,
      links: email.links,
      has_attachments: email.has_attachments
    });

    resultDiv.innerHTML = `
      <b>Score:</b> ${apiResponse.score}/100<br/>
      <b>Risque:</b> ${apiResponse.risk_level}<br/>
      <b>Raisons:</b><br/> ${apiResponse.reasons.map(r => "• " + r).join("<br/>")}
    `;
  } catch (err) {
    resultDiv.textContent = "Erreur: " + err.message;
  }
});
