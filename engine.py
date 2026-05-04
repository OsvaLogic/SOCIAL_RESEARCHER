import instaloader
import time
import random
import os
from collections import defaultdict
from typing import Tuple, List, Callable, Optional
import browser_cookie3

class InstagramEngine:
    def __init__(self, session_dir: str = "data/sessions"):
        self.session_dir = session_dir
        if not os.path.exists(self.session_dir):
            os.makedirs(self.session_dir)
            
        # Configuración core de Instaloader
        self.L = instaloader.Instaloader(
            quiet=True, 
            dirname_pattern=self.session_dir,
            request_timeout=30.0
        )
        
        # Evasión de 403 HTTP vía User-Agent
        self.L.context._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        })
        self.profile = None
        self.username = None

    def _random_sleep(self, min_time: float = 2.0, max_time: float = 5.0):
        """Delay anti-bot aleatorio."""
        time.sleep(random.uniform(min_time, max_time))

    def login(self, username: str) -> Tuple[bool, str]:
        """Autenticación vía clonación de cookies locales."""
        self.username = username

        try:
            cookies = None
            sessionid_found = False
            
            # Búsqueda de tokens por navegador
            for browser_fn in [browser_cookie3.firefox, browser_cookie3.chrome, browser_cookie3.edge, browser_cookie3.brave, browser_cookie3.opera]:
                try:
                    temp_cookies = browser_fn(domain_name='instagram.com')
                    if any(cookie.name == 'sessionid' for cookie in temp_cookies):
                        cookies = temp_cookies
                        sessionid_found = True
                        break
                except Exception:
                    continue
            
            if not sessionid_found:
                return False, "[!] SESIÓN NO ENCONTRADA O ARCHIVO BLOQUEADO. Cierra tu navegador por completo e intenta de nuevo."
                
            self.L.context._session.cookies.update(cookies)
            self.L.context.username = username
            
            # Inyección de X-CSRFToken para GraphQL
            for cookie in cookies:
                if cookie.name == 'csrftoken':
                    self.L.context._session.headers.update({'X-CSRFToken': cookie.value})
                    break
            
            # Validación
            self.profile = instaloader.Profile.from_username(self.L.context, username)
            return True, "Brecha de seguridad exitosa. Sesión clonada."
        except instaloader.exceptions.ProfileNotExistsException:
            return False, f"TARGET '{username}' INACCESIBLE (El usuario no existe)."
        except Exception as e:
            return False, f"ACCESO DENEGADO: {str(e)}"

    def get_followers_and_following(self, progress_callback: Callable[[float, str], None] = None) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Extracción y cruce relacional de audiencia."""
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        if progress_callback: progress_callback(0.2, "Descargando lista de seguidores...")
        followers = set(f.username for f in self.profile.get_followers())
        self._random_sleep(3, 6)
        
        if progress_callback: progress_callback(0.6, "Descargando lista de cuentas seguidas...")
        following = set(f.username for f in self.profile.get_followees())
        self._random_sleep(2, 4)

        if progress_callback: progress_callback(0.9, "Cruzando métricas...")
        not_following_back = list(following - followers)
        fans = list(followers - following)

        if progress_callback: progress_callback(1.0, "Análisis completado exitosamente.")
        
        return not_following_back, fans, list(followers), list(following)

    def get_interaction_ranking(self, progress_callback: Callable[[float, str], None] = None) -> List[Tuple[str, int]]:
        """Ranking de engagement (Comentarios=3, Stories=2, Likes=1)."""
        if not self.profile:
            raise ValueError("Sesión no iniciada.")

        scores = defaultdict(int)
        
        # 1. Escaneo de Historias activas
        if progress_callback: progress_callback(0.1, "Analizando visualizaciones de historias...")
        try:
            for story in self.L.get_stories(userids=[self.profile.userid]):
                for item in story.get_items():
                    for viewer in item.get_viewers():
                        scores[viewer.username] += 2
                    self._random_sleep(1, 2)
        except Exception:
            pass

        # 2. Escaneo de Posts recientes
        if progress_callback: progress_callback(0.2, "Recopilando interacciones de los últimos posts...")
        posts = self.profile.get_posts()
        
        for idx, post in enumerate(posts):
            if idx >= 5: 
                break
                
            progress = 0.2 + (0.8 * (idx / 5))
            if progress_callback: progress_callback(progress, f"Analizando post {idx+1}/5...")

            # Likes limits
            try:
                for count, like in enumerate(post.get_likes()):
                    if count >= 40: break
                    scores[like.username] += 1
            except Exception:
                pass 
            
            self._random_sleep(0.5, 1.5)

            # Comments limits
            try:
                for count, comment in enumerate(post.get_comments()):
                    if count >= 40: break
                    scores[comment.owner.username] += 3
            except Exception:
                pass
            
            self._random_sleep(0.5, 1.5)

        if progress_callback: progress_callback(1.0, "Ranking calculado exitosamente.")

        sorted_ranking = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_ranking[:10]