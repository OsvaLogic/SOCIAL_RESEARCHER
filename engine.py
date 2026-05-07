import instaloader
import time
import random
import os
from collections import defaultdict
from typing import Tuple, List, Callable, Optional
import browser_cookie3
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice

class InstagramEngine:
    def __init__(self, session_dir: str = "data/sessions"):
        self.session_dir = session_dir
        os.makedirs(self.session_dir, exist_ok=True)
            
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
            except Exception:
                pass
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

    def get_relational_data(self, progress_callback: Callable[[float, str], None] = None) -> dict:
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        if progress_callback:
            progress_callback(0.1, "Descargando followers/following en paralelo...")

        # Descarga paralela — 500 en lugar de 300 con misma velocidad gracias a más workers
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_followers = ex.submit(lambda: set(f.username for f in islice(self.profile.get_followers(), 500)))
            f_following = ex.submit(lambda: set(f.username for f in islice(self.profile.get_followees(), 500)))
            followers, following = f_followers.result(), f_following.result()

        not_following_back = list(following - followers)

        if progress_callback:
            progress_callback(0.45, "Escaneando celebridades (>3K followers)...")

        def check_celeb(uname):
            try:
                p = instaloader.Profile.from_username(self.L.context, uname)
                if p.followers > 3000:
                    return {
                        "username": uname,
                        "followers_count": p.followers,
                        "follows_back": uname in followers,
                    }
            except Exception:
                pass
            return None

        # 80 perfiles, 16 hilos — más cobertura sin penalizar velocidad
        scan_sample = list(following)[:80]
        celebrities = []
        with ThreadPoolExecutor(max_workers=16) as ex:
            for res in ex.map(check_celeb, scan_sample):
                if res:
                    celebrities.append(res)

        celebrities.sort(key=lambda x: x["followers_count"], reverse=True)

        if progress_callback:
            progress_callback(1.0, "Análisis completado.")

        return {
            "not_following": not_following_back,
            "celebrities": celebrities,
            "followers": list(followers),
        }

    def get_interaction_ranking(self, followers_list: list, progress_callback: Callable[[float, str], None] = None) -> dict:
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        scores = defaultdict(int)

        if progress_callback:
            progress_callback(0.1, "Analizando interacciones...")

        def process_post(post):
            local_scores = defaultdict(int)
            try:
                for i, like in enumerate(post.get_likes()):
                    if i >= 20: break          # Ampliado de 10 → 20
                    local_scores[like.username] += 1
            except Exception:
                pass
            try:
                for i, comment in enumerate(post.get_comments()):
                    if i >= 20: break          # Ampliado de 10 → 20
                    local_scores[comment.owner.username] += 3
            except Exception:
                pass
            return local_scores

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

        ghost_pool = set(followers_list) - set(scores.keys())
        ghosts = random.sample(list(ghost_pool), min(15, len(ghost_pool)))

        return {"top": top, "bottom": ghosts}