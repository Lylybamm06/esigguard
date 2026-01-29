// CONFIGURATION
const API_URL = "http://48.220.33.173:5106"; 

document.addEventListener('DOMContentLoaded', () => {
    loadHistory(); // On charge l'historique au lancement

    // --- CLIC SUR LE BOUTON SCANNER ---
    document.getElementById('scanBtn').addEventListener('click', () => {
        updateStatus("Extraction...");

        // 1. On parle au content.js
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            chrome.tabs.sendMessage(tabs[0].id, {action: "extractEmailData"}, (payload) => {
                
                // Gestion d'erreur (si on n'est pas sur Gmail)
                if (chrome.runtime.lastError || !payload) {
                    alert("Impossible de lire. Êtes-vous sur un onglet Gmail ?");
                    updateStatus("Erreur");
                    return;
                }

                // 2. On affiche IMMÉDIATEMENT une ligne "En cours" (Gris)
                const newAnalysis = {
                    id: Date.now(),
                    subject: payload.subject,
                    sender: payload.sender.address,
                    status: 'pending', 
                    score: 0, 
                    timestamp: new Date().toISOString()
                };
                saveAndDisplay(newAnalysis);
                updateStatus("Envoi au serveur...");

                // 3. ENVOI RÉEL (Fetch vers l'API de David)
                fetch(`${API_URL}/analyze`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(response => response.json())
                .then(data => {
                    updateStatus("Analyse en cours...");
                    // Optionnel : Si l'API renvoie tout de suite un ID, on pourrait le stocker
                })
                .catch(err => {
                    console.error("Erreur connexion:", err);
                    updateStatus("Serveur injoignable (Mode Démo)");
                    
                    // --- MODE DÉMO (Pour tester le visuel sans serveur) ---
                    // À SUPPRIMER QUAND LE SERVEUR MARCHERA
                    setTimeout(() => {
                        // Génère un score aléatoire pour voir les couleurs
                        const demoScore = Math.floor(Math.random() * 100);
                        updateAnalysisResult(newAnalysis.id, demoScore);
                    }, 2500);
                });
            });
        });
    });

    // Bouton Vider
    document.getElementById('clearBtn').addEventListener('click', () => {
        chrome.storage.local.set({history: []}, loadHistory);
    });
});

// --- GESTION DE L'AFFICHAGE ---
function loadHistory() {
    chrome.storage.local.get({history: []}, (result) => {
        const list = document.getElementById('email-list');
        list.innerHTML = '';

        // On inverse pour avoir les plus récents en haut
        result.history.reverse().forEach(item => {
            const li = document.createElement('li');
            li.className = 'email-card';

            // DÉFINITION DES COULEURS (Vert / Orange / Rouge)
            let color = '#334155'; // Gris (Pending)
            if (item.status === 'done') {
                if (item.score < 30) color = '#10b981';      // Vert (Sûr)
                else if (item.score < 70) color = '#f59e0b'; // Orange
                else color = '#ef4444';                      // Rouge (Danger)
            }

            // Calcul du remplissage du cercle
            const percent = item.status === 'pending' ? '0%' : `${item.score}%`;
            const scoreText = item.status === 'pending' ? '...' : item.score;

            li.innerHTML = `
                <div class="card-info">
                    <div class="subject" title="${item.subject}">${item.subject}</div>
                    <div class="sender">${item.sender}</div>
                </div>
                <div class="score-circle" 
                     style="--percent: ${percent}; --color: ${color};" 
                     data-score="${scoreText}">
                </div>
            `;

            // Clic pour détails
            li.addEventListener('click', () => {
                if(item.status === 'pending') alert("Analyse en cours... Veuillez patienter.");
                else alert(`DÉTAILS DU SCORE\n\nSujet : ${item.subject}\nScore : ${item.score}/100\n\n(Ici s'affichera l'explication IA)`);
            });

            list.appendChild(li);
        });
    });
}

// --- SAUVEGARDE ---
function saveAndDisplay(item) {
    chrome.storage.local.get({history: []}, (result) => {
        const newHistory = [...result.history, item];
        chrome.storage.local.set({history: newHistory}, loadHistory);
    });
}

// --- MISE À JOUR DU RÉSULTAT ---
function updateAnalysisResult(id, finalScore) {
    chrome.storage.local.get({history: []}, (result) => {
        const updated = result.history.map(item => {
            if (item.id === id) return { ...item, status: 'done', score: finalScore };
            return item;
        });
        chrome.storage.local.set({history: updated}, loadHistory);
    });
}

function updateStatus(msg) {
    document.getElementById('status-text').textContent = msg;
}