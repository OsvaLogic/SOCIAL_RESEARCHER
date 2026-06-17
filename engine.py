import instaloader
import time
import random
import os
import sqlite3
import logging
from contextlib import closing
from collections import defaultdict
from typing import Tuple, List, Callable, Optional
from datetime import datetime
import browser_cookie3
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice

logger = logging.getLogger(__name__)

class InstagramEngine:
    def __init__(self, session_dir: str = "data/sessions", db_path: str = "data/history.db"):
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)
        self.db_path = db_path
            
        self.L = instaloader.Instaloader(
            quiet=True, 
            dirname_pattern=self.session_dir,
            request_timeout=8.0,        # Reducido de 10s
            max_connection_attempts=1
        )
        
        self.L.context._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'X-IG-App-ID': '936619743392459',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin'
        })
        self.profile = None
        self.username = None
        self._init_db()

    def _init_db(self):
        """Inicializa la base de datos SQLite local para el historial de la Máquina del Tiempo."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn: # Maneja el commit/rollback
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS followers_history (
                        username TEXT,
                        follower_id TEXT,
                        last_seen TIMESTAMP,
                        PRIMARY KEY (username, follower_id)
                    )
                ''')

    def login(self, username: str) -> Tuple[bool, str]:
        self.username = username

        BROWSERS = [
            browser_cookie3.firefox,
            browser_cookie3.chrome,
            browser_cookie3.edge,
            browser_cookie3.brave,
            browser_cookie3.opera,
        ]

        cookies = None
        # Búsqueda paralela de cookies entre navegadores
        def try_browser(fn):
            try:
                c = fn(domain_name='instagram.com')
                if any(cookie.name == 'sessionid' for cookie in c):
                    return c
            except Exception as e:
                logger.debug(f"No se pudieron extraer cookies de un navegador: {e}")
            return None

        with ThreadPoolExecutor(max_workers=len(BROWSERS)) as ex:
            futures = {ex.submit(try_browser, fn): fn for fn in BROWSERS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    cookies = result
                    # Cancela el resto implícitamente al salir del bloque
                    break

        if not cookies:
            return False, "[!] SESIÓN NO ENCONTRADA. Cierra tu navegador e intenta de nuevo."

        self.L.context._session.cookies.update(cookies)
        self.L.context.username = username

        # Extracción de tokens en una sola pasada
        for cookie in cookies:
            name, value = cookie.name, cookie.value
            if name == 'csrftoken':
                self.L.context._session.headers['X-CSRFToken'] = value
            elif name == 'ig_did':
                self.L.context._session.headers['ig_did'] = value
            elif name == 'mid':
                self.L.context._session.headers['x-mid'] = value

        try:
            self.profile = instaloader.Profile.from_username(self.L.context, username)
            return True, "Sesión clonada correctamente."
        except instaloader.exceptions.ProfileNotExistsException:
            return False, f"Usuario '{username}' no existe."
        except Exception as e:
            return False, f"Error de acceso: {str(e)}"

    def _track_history(self, current_followers: set) -> dict:
        """Compara los seguidores actuales con la base de datos para encontrar Unfollowers y Nuevos."""
        if not self.username: return {"unfollowers": [], "new_followers": []}
        unfollowers, new_followers = [], []
        
        with closing(sqlite3.connect(self.db_path)) as conn:
            with conn:
                cursor = conn.cursor()
                cursor.execute('SELECT follower_id FROM followers_history WHERE username = ?', (self.username,))
                last_followers = set(row[0] for row in cursor.fetchall())
                
                if last_followers: # Si hay historial previo
                    unfollowers = list(last_followers - current_followers)
                    new_followers = list(current_followers - last_followers)
                    
                    # OPTIMIZACIÓN: Ejecución en bloque (Bulk Delete)
                    if unfollowers:
                        cursor.executemany('DELETE FROM followers_history WHERE username = ? AND follower_id = ?', [(self.username, uf) for uf in unfollowers])
                        
                now = datetime.now().isoformat()
                
                # OPTIMIZACIÓN: Ejecución en bloque (Bulk Insert)
                new_to_insert = current_followers - last_followers
                if new_to_insert:
                    cursor.executemany('INSERT INTO followers_history (username, follower_id, last_seen) VALUES (?, ?, ?)', [(self.username, nf, now) for nf in new_to_insert])
            
        return {"unfollowers": unfollowers, "new_followers": new_followers}

    def get_relational_data(self, progress_callback: Callable[[float, str], None] = None) -> dict:
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        if progress_callback:
            progress_callback(0.1, "Descargando followers/following en paralelo...")

        # Extracción completa sin truncamiento (Precisión del 100% para la BD)
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_followers = ex.submit(lambda: set(f.username for f in self.profile.get_followers()))
            f_following_objs = ex.submit(lambda: list(self.profile.get_followees()))
            followers, following_profiles = f_followers.result(), f_following_objs.result()

        following = set(p.username for p in following_profiles)
        not_following_back = list(following - followers)

        if progress_callback:
            progress_callback(0.45, "Escaneando celebridades (Motor Zero-Request)...")

        # ⚡ OPTIMIZACIÓN EXTREMA: En lugar de hacer 80 peticiones HTTP a perfiles aleatorios,
        # filtramos cuentas verificadas en memoria (0 peticiones) y solo consultamos esas.
        # Esto reduce el tiempo de escaneo drásticamente.
        verified_users = [p for p in following_profiles if p.is_verified]

        def check_celeb(p):
            try:
                # Solo aquí se hace la petición de red para ver los followers exactos
                if p.followers > 3000:
                    return {
                        "username": p.username,
                        "followers_count": p.followers,
                        "follows_back": p.username in followers,
                    }
            except Exception as e:
                logger.debug(f"Error analizando verificados ({p.username}): {e}")
            return None

        celebrities = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for res in ex.map(check_celeb, verified_users):
                if res:
                    celebrities.append(res)

        celebrities.sort(key=lambda x: x["followers_count"], reverse=True)

        if progress_callback:
            progress_callback(1.0, "Análisis completado.")

        # ⏳ Ejecutar Máquina del Tiempo
        if progress_callback: progress_callback(1.0, "Consultando base de datos temporal (SQLite)...")
        history_data = self._track_history(followers)

        return {
            "not_following": not_following_back,
            "celebrities": celebrities,
            "followers": list(followers),
            "history": history_data
        }

    def get_interaction_ranking(self, followers_list: list, progress_callback: Callable[[float, str], None] = None) -> dict:
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        scores = defaultdict(int)

        if progress_callback:
            progress_callback(0.1, "Analizando interacciones...")

        def process_post(post):
            likes_sc = defaultdict(int)
            comms_sc = defaultdict(int)
            
            def get_lks():
                try:
                    for i, like in enumerate(post.get_likes()):
                        if i >= 20: break
                        likes_sc[like.username] += 1
            except Exception as e:
                logger.debug(f"Error procesando likes: {e}")
                
            def get_cms():
                try:
                    for i, comment in enumerate(post.get_comments()):
                        if i >= 20: break
                        comms_sc[comment.owner.username] += 3
                except Exception as e:
                    logger.debug(f"Error procesando comentarios: {e}")

            # ⚡ OPTIMIZACIÓN: Descarga likes y comentarios en paralelo para el MISMO post.
            with ThreadPoolExecutor(max_workers=2) as ex:
                ex.submit(get_lks)
                ex.submit(get_cms)

            for k, v in comms_sc.items():
                likes_sc[k] += v
            return likes_sc

        # Analiza los últimos 3 posts en paralelo en lugar de solo 1
        recent_posts = list(islice(self.profile.get_posts(), 3))
        with ThreadPoolExecutor(max_workers=3) as ex:
            for partial in ex.map(process_post, recent_posts):
                for user, pts in partial.items():
                    scores[user] += pts

        if progress_callback:
            progress_callback(1.0, "Ranking calculado.")

        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:15]
        if not top:
            top = [("[SIN DATOS]", 0)]

        followers_set = set(followers_list)
        ghost_pool = followers_set - set(scores.keys())
        ghosts = random.sample(list(ghost_pool), min(15, len(ghost_pool)))

        # NUEVA FUNCIONALIDAD: Admiradores Secretos / Espías (Interactúan pero NO te siguen)
        secret_admirers = [(user, pts) for user, pts in scores.items() if user not in followers_set and user != self.username]
        secret_admirers.sort(key=lambda x: x[1], reverse=True)

        return {"top": top, "bottom": ghosts, "secret_admirers": secret_admirers[:10]}