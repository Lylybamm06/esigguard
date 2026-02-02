"""
Orchestrateur - Coordonne tous les microservices
Port : 5002
Version améliorée : nettoyage + explications propres
"""

from flask import Flask, jsonify
import os
import sys
import requests
import time
import json
from pathlib import Path
import shutil

sys.path.insert(0, '/app')
from database.database import get_db

app = Flask(__name__)

RESULTS_DIR = "/mnt/results"

SERVICES = {
    "smtp": "http://smtp:5007",
    "auth": "http://auth:5003",
    "lien": "http://lien:5004",
    "file": "http://file:5005",
    "content": "http://content:5006"
}

def reset_results_directory(analysis_id):
    """Supprime l'ancien dossier et recrée un dossier propre"""
    analysis_dir = Path(RESULTS_DIR) / f"analysis_{analysis_id}"
    if analysis_dir.exists():
        shutil.rmtree(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)
    return analysis_dir

def save_result(analysis_id, service_name, result_data):
    try:
        analysis_dir = Path(RESULTS_DIR) / f"analysis_{analysis_id}"
        result_file = analysis_dir / f"{service_name}_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Sauvegardé: {result_file}")
    except Exception as e:
        print(f"  ⚠  Erreur sauvegarde {service_name}: {e}")

def wait_for_service(service_name, url, max_retries=30):
    for _ in range(max_retries):
        try:
            r = requests.get(f"{url}/health", timeout=2)
            if r.status_code == 200:
                print(f"✅ {service_name} prêt")
                return True
        except:
            pass
        time.sleep(1)
    print(f"❌ {service_name} non disponible")
    return False

def call_service(service_name, url, analysis_id):
    try:
        print(f"  → Appel {service_name}...")
        r = requests.post(f"{url}/analyze/{analysis_id}", timeout=30)

        if r.status_code == 200:
            data = r.json()
            score = data.get("score", 0)
            print(f"    ✅ {service_name}: {score}/100")
            save_result(analysis_id, service_name.lower(), data)
            return data

        print(f"    ❌ {service_name}: Erreur HTTP {r.status_code}")
        return {"score": 0, "explanation": f"{service_name}: Erreur HTTP {r.status_code}"}

    except Exception as e:
        print(f"    ❌ {service_name}: {str(e)}")
        return {"score": 0, "explanation": f"{service_name}: Erreur ({str(e)})"}

def orchestrate_analysis(analysis_id):
    print(f"\n{'='*60}")
    print(f"🎯 ORCHESTRATION - Analyse {analysis_id}")
    print(f"{'='*60}\n")

    # Nettoyage du dossier
    reset_results_directory(analysis_id)

    results = {}

    print("📧 ÉTAPE 1/5 : SMTP")
    results["smtp"] = call_service("SMTP", SERVICES["smtp"], analysis_id)

    print("\n🔐 ÉTAPE 2/5 : Auth")
    results["auth"] = call_service("Auth", SERVICES["auth"], analysis_id)

    print("\n🔗 ÉTAPE 3/5 : Lien")
    results["lien"] = call_service("Lien", SERVICES["lien"], analysis_id)

    print("\n📎 ÉTAPE 4/5 : File")
    results["file"] = call_service("File", SERVICES["file"], analysis_id)

    print("\n📝 ÉTAPE 5/5 : Content")
    results["content"] = call_service("Content", SERVICES["content"], analysis_id)

    print(f"\n{'='*60}")
    print("📊 CALCUL DU SCORE FINAL")
    print(f"{'='*60}")

    scores = [data.get("score", 0) for data in results.values()]
    average_score = round(sum(scores) / len(scores), 2)

    print("\nScores individuels:")
    for service, data in results.items():
        print(f"  • {service.upper():10} : {data.get('score', 0)}/100")

    print(f"\n  🎯 MOYENNE : {average_score}/100")

    # Explication globale SANS erreurs techniques
    explanations = []
    for service_name in ["auth", "smtp", "lien", "file", "content"]:
        exp = results[service_name].get("explanation", "")
        if exp and "Erreur" not in exp:
            explanations.append(exp)

    explanation_cyber = " | ".join(explanations)

    print(f"\n💾 Mise à jour MySQL...")
    try:
        db = get_db()
        db.update_cyber_results(analysis_id, explanation_cyber, average_score)
        print("✅ MySQL mis à jour")
    except Exception as e:
        print(f"❌ Erreur MySQL: {str(e)}")

    final_result = {
        "analysis_id": analysis_id,
        "score_cyber": average_score,
        "explanation_cyber": explanation_cyber,
        "details": results
    }

    save_result(analysis_id, "orchestrator", final_result)

    print(f"\n{'='*60}")
    print("✅ ORCHESTRATION TERMINÉE")
    print(f"📁 Résultats dans: /mnt/results/analysis_{analysis_id}/")
    print(f"{'='*60}\n")

    return final_result

@app.route('/')
def home():
    return jsonify({
        "service": "Orchestrator",
        "port": 5002,
        "services": list(SERVICES.keys()),
        "results_dir": RESULTS_DIR
    })

@app.route('/health')
def health():
    try:
        db = get_db()
        conn = db.get_connection()
        conn.close()
        return jsonify({"status": "healthy"})
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@app.post("/orchestrate/<int:analysis_id>")
def orchestrate(analysis_id):
    try:
        return jsonify(orchestrate_analysis(analysis_id))
    except Exception as e:
        print(f"❌ Erreur orchestration: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🎯 ORCHESTRATOR - Port 5002")
    print("Version améliorée")
    print(f"📁 Résultats: {RESULTS_DIR}")
    print("="*60)

    print("\n🔍 Vérification des services...")
    for name, url in SERVICES.items():
        wait_for_service(name, url)

    print("="*60 + "\n")
    app.run(host="0.0.0.0", port=5002, debug=True)
