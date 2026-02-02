import json
import os

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except:
        return {}

if __name__ == "__main__":
    report = load_json("/results/report.json")

    score = 0

    # Exemple : score basé sur les liens
    links = report.get("links", {})
    score += links.get("moyenne_pourcentage", 0)

    # Exemple : score basé sur le contenu IA
    content = report.get("content", {})
    ai = content.get("ai_content_analysis", {})
    if ai.get("global_verdict") == "dangereux":
        score += 50
    elif ai.get("global_verdict") == "suspect":
        score += 25

    final = {
        "analysis_id": report.get("analysis_id"),
        "global_score": round(score, 2)
    }

    with open("/results/report_scored.json", "w") as f:
        json.dump(final, f, indent=4)

    print("[REPORT] Score global généré.")
