// content.js - Le photographe qui attend l'ordre

console.log("ESIG'Guard: Content Script prêt à scanner sur demande.");

// On écoute les messages venant du popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    
    if (request.action === "extractEmailData") {
        console.log("Ordre de scan reçu ! Extraction en cours...");

        // --- DÉBUT DE TON CODE D'EXTRACTION ---
        // (J'ai repris exactement ta logique, juste nettoyé pour correspondre au JSON de David)

        const subject = document.querySelector('h2.hP')?.innerText || "Sujet non trouvé";
        
        const senderNode = document.querySelector('.gD');
        const senderName = senderNode?.innerText || "Inconnu";
        const senderEmail = senderNode?.getAttribute('email') || "Inconnu";
        const bodyText = document.querySelector('.a3s')?.innerText.substring(0, 500) + "..." || "";

        const allLinks = document.querySelectorAll('.a3s a');
        const extractedUrls = [];
        allLinks.forEach((link) => {
            if (link.href && link.href.startsWith('http')) extractedUrls.push(link.href);
        });

        const attachmentNodes = document.querySelectorAll('.aV3, .aQa');
        const extractedAttachments = [];
        attachmentNodes.forEach((node) => {
            const fileName = node.innerText;
            if (fileName && fileName.trim() !== "") {
                extractedAttachments.push(fileName); // On envoie juste le nom pour l'instant, comme dans le cURL
            }
        });
        // --- FIN DE TON CODE D'EXTRACTION ---


        // ON FORMATE LE JSON EXACTEMENT COMME LE DEMANDE DAVID (voir ton image cURL)
        const payloadForServer = {
            "sender": {
                "address": senderEmail,
                "name": senderName
            },
            "subject": subject,
            "body_snippet": bodyText,
            "urls": extractedUrls,
            "attachments": extractedAttachments,
            // On ajoute un timestamp ISO pour faire pro
            "timestamp": new Date().toISOString() 
        };

        // C'est crucial : on renvoie les données au popup
        sendResponse(payloadForServer);
    }
    // Nécessaire pour que la réponse asynchrone fonctionne
    return true;
});