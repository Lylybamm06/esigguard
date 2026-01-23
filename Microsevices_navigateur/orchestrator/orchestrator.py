from flask import Flask, request, jsonify
import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
from pathlib import Path

app = Flask(__name__)

# Dossier de stockage
STORAGE_DIR = Path("/app/storage")
STORAGE_DIR.mkdir(exist_ok=True)

# URLs des microservices
SERVICES = {
    "auth": "http://auth:5002/analyze",
    "content": "http://content:5002/content",
    "file": "http://file:5002/files",
    "lien": "http://lien:5002/links"
}

@app.route('/')
def home():
    """Route racine pour vérifier que le service fonctionne"""
    return jsonify({
        "status": "running",
        "service": "Phishing Detection Orchestrator",
        "version": "1.0",
        "endpoints": {
            "analyze": {
                "method": "POST",
                "url": "/analyze",
                "description": "Analyse un email pour détecter le phishing"
            },
            "results": {
                "method": "GET",
                "url": "/results",
                "description": "Récupère les derniers résultats d'analyse"
            }
        },
        "available_services": list(SERVICES.keys())
    })

@app.route('/results')
def get_results():
    """Récupère les derniers résultats d'analyse"""
    try:
        results = {}
        
        # Lire chaque fichier de résultat
        for service in ["auth", "content", "file", "lien", "global"]:
            file_path = STORAGE_DIR / f"analysis_{service}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    results[service] = json.load(f)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def call_service(service_name, url, payload):
    """Appelle un microservice et retourne le résultat"""
    try:
        response = requests.post(url, json=payload, timeout=30)
        return service_name, response.json()
    except Exception as e:
        return service_name, {"error": str(e)}

@app.post("/analyze")
def analyze_email():
    """Route unique qui appelle tous les microservices en parallèle"""
    payload = request.json
    
    print("\n===== ORCHESTRATEUR : ANALYSE GLOBALE =====")
    print(f"Payload reçu: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    results = {}
    
    # Appeler tous les services en parallèle
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(call_service, name, url, payload): name 
            for name, url in SERVICES.items()
        }
        
        for future in as_completed(futures):
            service_name, result = future.result()
            results[service_name] = result
            print(f"\n[{service_name.upper()}] Analyse terminée")
    
    # Résultat global
    timestamp = datetime.utcnow()
    
    global_result = {
        "email_info": {
            "sender": payload.get("sender", {}).get("address", ""),
            "subject": payload.get("subject", ""),
            "timestamp": payload.get("timestamp", "")
        },
        "analysis": results,
        "analyzed_at": timestamp.isoformat(),
        "original_payload": payload
    }
    
    # Sauvegarder chaque résultat dans un fichier séparé
    try:
        # 1. Sauvegarder le résultat de auth
        with open(STORAGE_DIR / "analysis_auth.json", 'w', encoding='utf-8') as f:
            json.dump({
                "service": "auth",
                "analyzed_at": timestamp.isoformat(),
                "result": results.get("auth", {}),
                "email_info": global_result["email_info"]
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ analysis_auth.json sauvegardé")
        
        # 2. Sauvegarder le résultat de content
        with open(STORAGE_DIR / "analysis_content.json", 'w', encoding='utf-8') as f:
            json.dump({
                "service": "content",
                "analyzed_at": timestamp.isoformat(),
                "result": results.get("content", {}),
                "email_info": global_result["email_info"]
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ analysis_content.json sauvegardé")
        
        # 3. Sauvegarder le résultat de file
        with open(STORAGE_DIR / "analysis_file.json", 'w', encoding='utf-8') as f:
            json.dump({
                "service": "file",
                "analyzed_at": timestamp.isoformat(),
                "result": results.get("file", {}),
                "email_info": global_result["email_info"]
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ analysis_file.json sauvegardé")
        
        # 4. Sauvegarder le résultat de lien
        with open(STORAGE_DIR / "analysis_lien.json", 'w', encoding='utf-8') as f:
            json.dump({
                "service": "lien",
                "analyzed_at": timestamp.isoformat(),
                "result": results.get("lien", {}),
                "email_info": global_result["email_info"]
            }, f, indent=2, ensure_ascii=False)
        print(f"✅ analysis_lien.json sauvegardé")
        
        # 5. Sauvegarder le résultat global
        with open(STORAGE_DIR / "analysis_global.json", 'w', encoding='utf-8') as f:
            json.dump(global_result, f, indent=2, ensure_ascii=False)
        print(f"✅ analysis_global.json sauvegardé")
        
        print(f"\n✅ Tous les fichiers sauvegardés dans {STORAGE_DIR}")
        
    except Exception as e:
        print(f"\n❌ Erreur lors de la sauvegarde: {str(e)}")
        global_result["save_error"] = str(e)
    
    print("\n===== RÉSULTAT GLOBAL =====")
    print(json.dumps(global_result, indent=2, ensure_ascii=False))
    print("============================\n")
    
    return jsonify(global_result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
