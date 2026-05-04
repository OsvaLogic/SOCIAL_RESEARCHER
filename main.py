import os
import webbrowser
from threading import Timer
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from engine import InstagramEngine

app = Flask(__name__, template_folder=".", static_folder=".")

@app.route("/")
def home():
    return render_template("template.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    username = data.get("username", "").strip().replace("@", "")
    
    if not username:
        return jsonify({"error": "El usuario es obligatorio"})
        
    engine = InstagramEngine()
    
    print(f"\n[*] INICIANDO BRECHA PARA TARGET: @{username}")
    print("[-] Extrayendo llaves de seguridad del navegador local...")
    success, msg = engine.login(username)
    if not success:
        print(f"[!] FALLO: {msg}")
        return jsonify({"error": msg})
        
    def server_progress(value: float, text: str):
        print(f"    -> {text}")

    try:
        not_following, fans, followers, following = engine.get_followers_and_following(server_progress)
        ranking = engine.get_interaction_ranking(server_progress)
        
        print("\n[+] EXTRACCIÓN EXITOSA. Transfiriendo datos al Dashboard...")
        return jsonify({
            "success": True,
            "not_following": not_following,
            "fans": fans,
            "followers": followers,
            "following": following,
            "ranking": ranking,
            "date": datetime.now().strftime("%d de %B, %Y a las %H:%M:%S")
        })
    except Exception as e:
        return jsonify({"error": f"Error durante el análisis: {str(e)}"})

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 INICIANDO SERVIDOR WEB (NO CIERRES ESTA VENTANA) 🚀")
    print("=" * 60)
    Timer(1.0, open_browser).start()
    app.run(port=5000, debug=False)