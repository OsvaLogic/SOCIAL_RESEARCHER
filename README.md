# 🕵️‍♂️ SOCIAL RESEARCHER

![Version](https://img.shields.io/badge/Versi%C3%B3n-1.1-00f3ff?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-ff003c?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web_Server-00ff41?style=for-the-badge&logo=flask&logoColor=black)

> **¡Actualización a la Versión (v1.1)!** 🚀  
> Una herramienta de inteligencia local avanzada para analizar perfiles de Instagram. Olvídate de los bloqueos y contraseñas: este sistema extrae silenciosamente la sesión de tu navegador local y despliega los datos en un Dashboard inmersivo con estética Cyberpunk y ASUS ROG.

## ✨ Características Principales
* 🔐 **Auth Bypass Local:** Extrae la sesión local (`sessionid` y `csrftoken`) de tu navegador para evadir el Error 403 y los mecanismos antibot. ¡No necesitas entregar tu contraseña al script!
* ⚡ **Motor Fast-Slice Multihilo:** Extracción de datos en tiempo récord (segundos) saltando las restricciones de red mediante peticiones concurrentes y límites inteligentes.
* 🕸️ **Estado Relacional:** Descubre al instante quiénes sigues pero no te siguen de vuelta, y rastrea celebridades de más de 3,000 seguidores.
* 🏆 **Núcleo de Interacciones:** Algoritmo veloz que separa a tus *Top Stalkers* (quienes más interactúan) de los *Fantasmas* (seguidores con 0 interacción).
* 💻 **Dashboard High-Tech:** Una interfaz inmersiva (Dark/Espacio) construida con Flask y Particles.js, limpia y sin rodeos.
* 💾 **Exportación de Reportes:** Descarga todos los resultados y clasificaciones en un reporte unificado `.csv` con un solo clic.

## ⚙️ Requisitos Previos
* **Python 3.10** o superior.
* Un navegador web (Firefox, Chrome, Edge, Brave o Opera).
* Tener tu **sesión de Instagram iniciada** de forma habitual en tu navegador.

## 🛠️ Instalación

1. Clona o descarga este repositorio en tu computadora.
2. Abre una terminal en la carpeta del proyecto e instala las dependencias necesarias:
```bash
pip install -r requirements.txt
```

## 🚀 Modo de Uso

1. **Prepara el entorno:** Abre tu navegador favorito, entra a `instagram.com` y asegúrate de tener tu sesión activa.
2. **Inicia el Servidor Local:** En tu terminal, ejecuta el siguiente comando:
```bash
python main.py
```
3. **Accede a la Terminal Web:** El sistema abrirá automáticamente una pestaña en tu navegador web en `http://127.0.0.1:5000/`.
4. **Inicia la Brecha:** Ingresa el nombre de usuario de la cuenta (`TARGET_USERNAME`) y haz clic en "EJECUTAR ENLACE" para comenzar la extracción.

---

### 📌 Stack Tecnológico
* **Backend:** Python, Flask, Instaloader, browser-cookie3
* **Frontend:** HTML5, CSS3, JavaScript, Chart.js
* **Fuentes:** Google Fonts (Rajdhani, Share Tech Mono)

*⚠️ **Nota de responsabilidad:** Esta herramienta es de uso estrictamente educativo y de análisis personal. Realizar demasiadas peticiones a Instagram de forma abusiva puede resultar en limitaciones temporales de la API en tu cuenta.*