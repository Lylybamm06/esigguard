import json
import os

RESULTS_DIR = "/results"

MICROSERVICES = [
    "parsed.json",
    "auth.json",
    "smtp.json",
    "content.json",
    "links.json",
    "files.json"
]

def load_json(name):
    path = os.path.join(RESULTS_DIR, name)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

# Recherche récursive d'un champ dans un JSON
def find_field(data, field):
    if isinstance(data, dict):
        if field in data:
            return data[field]
        for v in data.values():
            result = find_field(v, field)
            if result is not None:
                return result
    if isinstance(data, list):
        for item in data:
            result = find_field(item, field)
            if result is not None:
                return result
    return None

if __name__ == "__main__":
    final = {}
    total_score = 0
    total_percentage = 0
    count_percentage = 0

    for filename in MICROSERVICES:
        data = load_json(filename)
        key = filename.replace(".json", "")
        final[key] = data

        # Recherche intelligente
        score = find_field(data, "score")
        pourcentage = find_field(data, "pourcentage")

        if score is not None:
            final[key]["_score"] = score
            total_score += score

        if pourcentage is not None:
            final[key]["_pourcentage"] = pourcentage
            total_percentage += pourcentage
            count_percentage += 1

    # Calculs finaux
    score_final = (total_score / 495) * 100 if total_score > 0 else 0
    pourcentage_final = (total_percentage / count_percentage) if count_percentage > 0 else 0

    final["score_final"] = round(score_final, 2)
    final["pourcentage_final"] = round(pourcentage_final, 2)

    with open(os.path.join(RESULTS_DIR, "final_scored_report.json"), "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    print("[REPORT] Rapport avec scores généré dans /results/final_scored_report.json")
