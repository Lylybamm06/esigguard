import os
import json
from common.parser_utils import parse_local_email
from groq import Groq

def analyser_contenu_ia(subject, texte):
    """Analyse le contenu avec Groq et renvoie un JSON propre au format demandé."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    prompt = f"""
Analyse cet email et renvoie UNIQUEMENT un JSON strictement au format suivant :

{{
  "content": {{
    "subject": "...",
    "ai_content_analysis": {{
      "global_verdict": "ok | suspect | dangereux",
      "phishing_indicators": {{
        "status": "ok | suspect | dangereux",
        "reason": "..."
      }},
      "language_quality": {{
        "status": "ok | suspect | dangereux",
        "reason": "..."
      }},
      "context_coherence": {{
        "status": "ok | suspect | dangereux",
        "reason": "..."
      }}
    }}
  }}
}}

Aucun texte avant ou après. Aucune phrase explicative. Juste le JSON.

Sujet :
\"\"\"{subject}\"\"\"

Contenu :
\"\"\"{texte}\"\"\"
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500
        
    )

    texte_ia = response.choices[0].message.content.strip()

    # Tentative de parsing direct
    try:
        return json.loads(texte_ia)
    except json.JSONDecodeError:
        # Extraction du JSON si l'IA ajoute du texte autour
        try:
            start = texte_ia.index("{")
            end = texte_ia.rindex("}") + 1
            return json.loads(texte_ia[start:end])
        except:
            return {"error": "Réponse IA non valide", "raw": texte_ia}


if __name__ == "__main__":
    eml_path = "/data/" + os.getenv("EMAIL_FILE", "email.eml")

    parsed = parse_local_email(eml_path)

    subject = parsed.get("subject", "")
    texte = parsed.get("body", "")

    analyse = analyser_contenu_ia(subject, texte)

    # Écriture JSON propre
    with open("/results/content.json", "w", encoding="utf-8") as f:
        json.dump(analyse, f, indent=4, ensure_ascii=False)

    print("[CONTENT] Analyse IA terminée. Résultat écrit dans /results/content.json")
