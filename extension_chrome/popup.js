document.addEventListener('DOMContentLoaded', () => {
    const list = document.getElementById('email-list');
    
    // 1. Récupérer les mails stockés
    chrome.storage.local.get({capturedEmails: []}, (result) => {
        const emails = result.capturedEmails;
        
        if (emails.length > 0) {
            list.innerHTML = ''; // Vider le message "Aucun mail..."
            
            emails.forEach(email => {
                const li = document.createElement('li');
                li.className = 'email-item';
                
                // Couleur du badge selon le score
                let badgeClass = 'risk-low';
                let riskLabel = 'SÛR';
                if (email.score > 70) { badgeClass = 'risk-high'; riskLabel = 'DANGER'; }
                else if (email.score > 30) { badgeClass = 'risk-med'; riskLabel = 'SUSPECT'; }

                li.innerHTML = `
                    <div class="row-top">
                        <span class="subject" title="${email.subject}">${email.subject}</span>
                        <span class="badge ${badgeClass}">${email.score}/100</span>
                    </div>
                    <div class="sender">${email.sender}</div>
                `;
                
                // Interaction : Click sur un mail
                li.addEventListener('click', () => {
                    alert(`Analyse détaillée lancée pour :\n${email.subject}\n\n(Connexion Backend en attente...)`);
                });

                list.appendChild(li);
            });
        }
    });

    // 2. Bouton Nettoyer
    document.getElementById('clearBtn').addEventListener('click', () => {
        chrome.storage.local.set({capturedEmails: []}, () => {
            list.innerHTML = '<li style="padding:20px; text-align:center; color:#999;">Liste vidée.</li>';
        });
    });
});