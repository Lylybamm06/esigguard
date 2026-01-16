function text(sel) {
  const el = document.querySelector(sel);
  return el ? el.innerText.trim() : "";
}

function getLinks() {
  const bodyEl = document.querySelector("div.a3s");
  if (!bodyEl) return [];
  return [...bodyEl.querySelectorAll("a[href]")]
    .map(a => a.href)
    .filter(h => h.startsWith("http"));
}

function extractEmail() {
  const subject = text("h2.hP");
  const sender = text(".gD") || text(".go");
  const body = text("div.a3s");
  const links = [...new Set(getLinks())];

  // heuristique pièces jointes (peut évoluer)
  const has_attachments = !!document.querySelector("div.aQH, div.aZo, div.aQw");

  return { subject, sender, body, links, has_attachments };
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "GET_EMAIL") {
    sendResponse({ ok: true, data: extractEmail() });
  }
});
