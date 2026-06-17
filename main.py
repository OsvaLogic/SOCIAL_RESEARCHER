import logging
import os
import webbrowser
from threading import Timer
from flask import Flask, request, jsonify, render_template
from datetime import datetime
from engine import InstagramEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=".", static_folder=".")

@app.route("/")
def home():
    return render_template("template.html")

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json or {}
    username = data.get("username", "").strip().replace("@", "")
    
    if not username:
        return jsonify({"error": "El usuario es obligatorio"})
        
    engine = InstagramEngine()
    
    logger.info(f"INICIANDO BRECHA PARA TARGET: @{username}")
    logger.info("Extrayendo llaves de seguridad del navegador local...")
    success, msg = engine.login(username)
    if not success:
        logger.error(f"FALLO: {msg}")
        return jsonify({"error": msg})
        
    def server_progress(value: float, text: str):
        logger.info(f"Progreso [{int(value * 100)}%]: {text}")

    try:
        relational_data = engine.get_relational_data(server_progress)
        ranking_data = engine.get_interaction_ranking(relational_data["followers"], server_progress)
        
        logger.info("EXTRACCIÓN EXITOSA. Transfiriendo datos al Dashboard...")
        return jsonify({
            "success": True,
            "not_following": relational_data["not_following"],
            "celebrities": relational_data["celebrities"],
            "top_interactions": ranking_data["top"],
            "least_interactions": ranking_data["bottom"],
            "secret_admirers": ranking_data["secret_admirers"],
            "recent_unfollowers": relational_data["history"]["unfollowers"],
            "new_followers": relational_data["history"]["new_followers"],
            "date": datetime.now().strftime("%d de %B, %Y a las %H:%M:%S")
        })
    except Exception as e:
        logger.exception("Error interno durante el análisis")
        return jsonify({"error": f"Error durante el análisis: {str(e)}"})

def open_browser():
    webbrowser.open_new("http://127.0.0.1:5000/")

if __name__ == "__main__":
    logger.info("🚀 INICIANDO SERVIDOR WEB (NO CIERRES ESTA VENTANA) 🚀")
    Timer(1.0, open_browser).start()
    app.run(port=5000, debug=False)