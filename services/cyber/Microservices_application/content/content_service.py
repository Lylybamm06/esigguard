from flask import Flask, jsonify
import os
import sys
import json
import traceback

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)


try:
    from groq import Groq
    GROQ_AVAILABLE = True
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if GROQ_API_KEY and GROQ_API_KEY != "votre_cle_groq":
        client = Groq(api_key=GROQ_API_KEY)
    else:
        client = None
        GROQ_AVAILABLE = False
except Exception as e:
    print(f"⚠️  Groq non disponible: {e}")
    GROQ_AVAILABLE = False
    client = None

def ai_analyze_content(subject, text_plain):
    """Analyse IA du contenu avec Groq"""
    
    
    if not GROQ_AVAILABLE or not client:
        print("⚠️  Analyse IA ignorée (Groq non disponible)")
        return {
            "global_verdict": "unknown",
            "phishing_indicators": {
                "status": "unknown",
                "reason": "Analyse IA non disponible (clé Groq manquante)"
            },
            "language_quality": {
                "status": "unknown",
                "reason": "Analyse IA non disponible"
            },
            "context_coherence": {
                "status": "unknown",
                "reason": "Analyse IA non disponible"
            }
        }
    
    prompt = f"""
Analyse ce mail selon trois axes et renvoie STRICTEMENT le JSON suivant :

{{
  "global_verdict": "...",
  "phishing_indicators": {{
    "status": "...",
    "reason": "..."
  }},
  "language_quality": {{
    "status": "...",
    "reason": "..."
  }},
  "context_coherence": {{
    "status": "...",
    "reason": "..."
  }}
}}

Règles STRICTES :
- "status" DOIT être exactement "ok" ou "suspect" (minuscules)
- "reason" = UNE phrase courte et précise (max 100 caractères)
- "global_verdict" = "coherent" si tout est ok, sinon "suspect"
- Analyse les indicateurs de phishing (urgence, menace, demande d'action)
- Vérifie la qualité linguistique (grammaire, orthographe, formulation)
- Vérifie la cohérence contextuelle (correspond-il à une vraie communication ?)

Email à analyser :
Sujet : {subject}
Corps : {text_plain[:1000]}

Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""

    try:
        print(" Appel Groq API...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.3
        )

        raw = response.choices[0].message.content.strip()
        print(f" Réponse Groq (raw): {raw[:200]}...")
        
        
        cleaned = raw
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        print(f" JSON nettoyé: {cleaned[:200]}...")

        
        result = json.loads(cleaned)
        print(f" JSON parsé avec succès")
        
        
        required_keys = ["global_verdict", "phishing_indicators", "language_quality", "context_coherence"]
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Clé manquante: {key}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f" Erreur JSON: {e}")
        print(f"   Contenu: {cleaned[:500]}")
        return {
            "global_verdict": "error",
            "phishing_indicators": {
                "status": "error",
                "reason": "Erreur parsing JSON IA"
            },
            "language_quality": {
                "status": "unknown",
                "reason": "Analyse non disponible"
            },
            "context_coherence": {
                "status": "unknown",
                "reason": "Analyse non disponible"
            }
        }
    except Exception as e:
        print(f" Erreur IA: {type(e).__name__}: {str(e)}")
        return {
            "global_verdict": "error",
            "phishing_indicators": {
                "status": "error",
                "reason": f"Erreur IA: {str(e)[:50]}"
            },
            "language_quality": {
                "status": "unknown",
                "reason": "Analyse non disponible"
            },
            "context_coherence": {
                "status": "unknown",
                "reason": "Analyse non disponible"
            }
        }

def analyze_keywords(subject):
    """Analyse des mots-clés suspects dans le sujet"""
    subject_lower = (subject or "").lower()
    score = 0
    keywords_found = []

    phishing_keywords = {
        'urgent': 20, 'action requise': 20, 'compte bloqué': 30,
        'vérification': 15, 'verification': 15, 'confirmez': 15,
        'confirm': 15, 'cliquez': 20, 'click here': 20,
        'félicitations': 15, 'congratulations': 15, 'gagné': 20,
        'won': 20, 'prize': 20, 'winner': 20, 'verify': 15,
        'account': 10, 'suspended': 25, 'expire': 15, '24h': 15,
        'immediately': 15, 'immédiat': 15, 'maintenant': 10,
        'now': 10, 'important': 10, 'sécurité': 15, 'security': 15
    }

    for keyword, points in phishing_keywords.items():
        if keyword in subject_lower:
            score += points
            keywords_found.append(keyword)

    print(f" Mots-clés trouvés: {keywords_found} (score: {score})")
    
    return {
        "keyword_score": min(100, score),
        "keywords_found": keywords_found,
        "count": len(keywords_found)
    }

def calculate_content_score(ai_result, keywords_result):
    
    score = 0
    
    
    if ai_result.get("phishing_indicators", {}).get("status") == "suspect":
        score += 15
        print("  +15 (phishing indicators)")
    
    if ai_result.get("language_quality", {}).get("status") == "suspect":
        score += 15
        print("  +15 (language quality)")
    
    if ai_result.get("context_coherence", {}).get("status") == "suspect":
        score += 30
        print("  +30 (context coherence)")
    
    
    if keywords_result["count"] > 0:
        kw_score = min(40, keywords_result["count"] * 10)
        score += kw_score
        print(f"  +{kw_score} (keywords)")
    
    final_score = min(100, score)
    print(f"📊 Score final: {final_score}/100")
    
    return final_score

def build_explanation(ai_result, keywords_result, score):
    """Construit l'explication textuelle"""
    parts = []
    
    
    phishing = ai_result.get("phishing_indicators", {})
    if phishing.get("status") == "suspect":
        parts.append(f"Phishing: {phishing.get('reason', 'detecte')}")
    
    
    language = ai_result.get("language_quality", {})
    if language.get("status") == "suspect":
        parts.append(f"Langue: {language.get('reason', 'suspecte')}")
    
    
    context = ai_result.get("context_coherence", {})
    if context.get("status") == "suspect":
        parts.append(f"Coherence: {context.get('reason', 'douteuse')}")
    
    
    if keywords_result["count"] > 0:
        kw_list = ", ".join(keywords_result["keywords_found"][:3])
        if keywords_result["count"] > 3:
            kw_list += f" (+{keywords_result['count'] - 3})"
        parts.append(f"Mots-cles: {kw_list}")
    
    if not parts:
        return (
            "Content: Aucun indicateur suspect."
            "Le message ne contient ni demande inhabituelle, ni urgence artificielle, "
            "et la formulation est coherente avec une communication légitime. "
            "Le sujet et le contenu sont alignes et ne presentent aucun signe de phishing."
        )
    
    return "Content: " + " | ".join(parts)

def analyze_content(analysis_id):
    """Analyse complète du contenu"""
    try:
        print(f"\n CONTENT - Analyse {analysis_id}")
        
        
        db = get_db()
        analysis = db.get_complete_analysis(analysis_id)

        if not analysis:
            raise ValueError(f"Analyse {analysis_id} introuvable")

        subject = analysis.get("email_subject", "") or ""
        body = analysis.get("email_body", "") or ""
        
        print(f" Sujet: {subject[:50]}...")
        print(f" Corps: {len(body)} caractères")

        
        print("\n Analyse mots-clés...")
        keywords_result = analyze_keywords(subject)
        
        
        print("\n Analyse IA...")
        ai_result = ai_analyze_content(subject, body)
        
        
        print("\n Calcul score...")
        score = calculate_content_score(ai_result, keywords_result)
        
        
        explanation = build_explanation(ai_result, keywords_result, score)
        
        print(f"\n Analyse terminée: {score}/100")

        return {
            "analysis_id": analysis_id,
            "service": "content",
            "score": score,
            "subject": subject,
            "keywords": keywords_result,
            "ai_content_analysis": ai_result,
            "explanation": explanation
        }
        
    except Exception as e:
        print(f"\n ERREUR dans analyze_content:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"   Traceback:")
        traceback.print_exc()
        raise

@app.route('/')
def home():
    return jsonify({"status": "running", "service": "Content", "port": 5006})

@app.route('/health')
def health():
    try:
        db = get_db()
        conn = db.get_connection()
        conn.close()
        
        status = {
            "status": "healthy",
            "groq_available": GROQ_AVAILABLE
        }
        
        if not GROQ_AVAILABLE:
            status["warning"] = "GROQ_API_KEY manquante ou invalide"
        
        return jsonify(status)
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.post("/analyze/<int:analysis_id>")
def analyze(analysis_id):
    try:
        result = analyze_content(analysis_id)
        return jsonify(result)
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        print(f" Erreur endpoint: {error_msg}")
        return jsonify({"error": error_msg}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" Content Service - Port 5006")
    print("Version robuste avec logs détaillés")
    print("="*60)
    
    
    if GROQ_AVAILABLE and client:
        print(" Groq API: Disponible")
    else:
        print("⚠️  Groq API: Non disponible (fonctionnement en mode dégradé)")
        print("   Seule l'analyse par mots-clés sera effectuée")
    
    print("="*60 + "\n")
    
    app.run(host="0.0.0.0", port=5006, debug=True)
