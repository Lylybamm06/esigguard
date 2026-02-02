from flask import Flask, jsonify, request
import json
import os
from datetime import datetime
from pathlib import Path
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


CONTENT_STORAGE = Path("./storage/content")
CONTENT_STORAGE.mkdir(parents=True, exist_ok=True)



def ai_analyze_content(text):
    prompt = f"""
    Analyse le contenu suivant et détermine s'il est suspect ou cohérent.
    Donne une raison claire et concise.

    Texte :
    {text}

    Réponds STRICTEMENT en JSON :
    {{
        "status": "...",
        "reason": "..."
    }}
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except Exception:
        return {
            "status": "unknown",
            "reason": f"Invalid JSON returned by Groq: {raw}"
        }


def calculate_content_score(ai_analysis):
    MAX_SCORE = 100
    score = 0
    details = []

    if ai_analysis.get("status") == "suspect":
        score += 100
        details.append({
            "indicator": "ai_content_analysis",
            "points": 100,
            "reason": ai_analysis.get("reason", "Contenu suspect")
        })

    percentage = round((score / MAX_SCORE) * 100, 2)
    risk_level = "high" if percentage >= 75 else "medium" if percentage >= 40 else "low"

    return score, percentage, risk_level, details


def check_content(parsed_email):

    
    text = parsed_email["email_data"].get("email_subject", "")

    ai_report = ai_analyze_content(text)
    score, percentage, risk_level, details = calculate_content_score(ai_report)

    explanation = ai_report.get("reason", "Aucune raison fournie")

    
    for trigger in ["tandis que", "réponse en JSON"]:
        if trigger in explanation:
            explanation = explanation.split(trigger)[0].strip()
            if explanation.endswith(",") or explanation.endswith("et"):
                explanation = explanation.rstrip(", et").strip()
            explanation += "."

    return {
        "content_analysis": ai_report,
        "score": score,
        "percentage": percentage,
        "risk_level": risk_level,
        "explanation": explanation
    }


app = Flask(__name__)

@app.post("/content")
def analyze_content():

    parsed = request.get_json(force=True)

    result = check_content(parsed)

    
    filename = CONTENT_STORAGE / f"content_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "parsed_email": parsed,
            "content_analysis": result,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2, ensure_ascii=False)

    print(f"[CONTENT] Analyse sauvegardée dans : {filename}")

    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5103)
