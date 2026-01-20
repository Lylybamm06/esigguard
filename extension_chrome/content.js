console.log("ESIG'Guard: Scanner actif (Mode Stable)");

let lastScannedSubject = ""; // Mémoire pour ne pas spammer

function showFullPayload() {
    // 1. CIBLAGE
    const emailContainer = document.querySelector('.h7') || document.querySelector('.gs');
    if (!emailContainer) return; 

    // 2. EXTRACTION TEXTE
    const subject = document.querySelector('h2.hP')?.innerText || "Sujet non trouvé";
    
    // STOP : Si on a déjà affiché ce mail, on ne fait rien. La console reste fixe.
    if (subject === lastScannedSubject) return;
    lastScannedSubject = subject; // On mémorise le nouveau sujet

    const senderNode = document.querySelector('.gD'); 
    const senderName = senderNode?.innerText || "Inconnu";
    const senderEmail = senderNode?.getAttribute('email') || "Inconnu";
    const bodyText = document.querySelector('.a3s')?.innerText.substring(0, 500) + "..." || ""; 

    // 3. EXTRACTION URLS
    const allLinks = document.querySelectorAll('.a3s a');
    const extractedUrls = [];
    allLinks.forEach((link) => {
        if (link.href && link.href.startsWith('http')) extractedUrls.push(link.href);
    });

    // 4. EXTRACTION PIÈCES JOINTES
    const attachmentNodes = document.querySelectorAll('.aV3, .aQa'); 
    const extractedAttachments = [];
    attachmentNodes.forEach((node) => {
        const fileName = node.innerText;
        if (fileName && fileName.trim() !== "") {
            const extension = fileName.split('.').pop().toLowerCase();
            extractedAttachments.push({
                "filename": fileName,
                "extension": extension,
                "risk_type": (['exe', 'bat', 'js', 'vbs'].includes(extension)) ? "CRITICAL" : "UNKNOWN"
            });
        }
    });

    // 5. EXTRACTION HEADER NINJA
    const detailsText = document.querySelector('.ajB')?.innerText || ""; 
    const mailedBy = detailsText.match(/mailed-by:\s*([^\n\r]*)/i)?.[1] || "non_disponible";
    const signedBy = detailsText.match(/signed-by:\s*([^\n\r]*)/i)?.[1] || "non_disponible";

    // 6. JSON FINAL
    const fullPayload = {
        "meta": { "source": "extension_chrome", "timestamp": new Date().toISOString() },
        "email_data": {
            "subject": subject,
            "sender": { "name": senderName, "address": senderEmail },
            "body_snippet": bodyText,
            "urls": extractedUrls, 
            "attachments": extractedAttachments,
            "technical_light": { "spf_indicator": mailedBy, "dkim_indicator": signedBy }
        }
    };

    // 7. AFFICHAGE (SANS CLEAR)
    console.log("--------------------------------------------------");
    console.log(`📨 NOUVEAU MAIL DÉTECTÉ : ${subject}`);
    console.log(fullPayload);
    
    if(extractedAttachments.length > 0) console.log(`📎 ${extractedAttachments.length} PJ détectées`);
    if(extractedUrls.length > 0) console.log(`🔗 ${extractedUrls.length} Liens détectés`);
}

// On vérifie s'il y a du nouveau toutes les 2 secondes
setInterval(showFullPayload, 2000);