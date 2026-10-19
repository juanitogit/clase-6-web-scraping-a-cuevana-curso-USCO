"""
================================================================================
GUÍA PEDAGÓGICA PARA EL DOCENTE: WEB SCRAPING CON SELENIUM WEBDRIVER
MÓDULO: AUTOMATIZACIÓN DE NAVEGADORES Y EXTRACCIÓN DINÁMICA (CUEVANA)
================================================================================

OBJETIVOS DE APRENDIZAJE:
1. Comprender la arquitectura de Selenium WebDriver (Protocolo W3C WebDriver).
2. Diferenciar entre Scraping Estático (Requests + BS4) y Scraping Basado en Navegador Real (Selenium).
3. Configurar ChromeOptions para optimizar rendimiento (modo headless, deshabilitar imágenes y GPU).
4. Eludir la detección de automatización básica (`AutomationControlled`, `navigator.webdriver`).
5. Manejar Esperas Explícitas (`WebDriverWait` + `expected_conditions`) vs esperas duras (`time.sleep`).
6. Localizar elementos del DOM mediante selectores CSS (`By.CSS_SELECTOR`) y extraer atributos (`get_attribute`).
7. Explicar el costo computacional: Selenium consume más RAM y tiempo de CPU que librerías HTTP ligeras,
   pero permite ejecutar código JavaScript, interactuar con single-page applications (SPA) y sortear anti-bots.

REQUISITOS PREVIOS:
- selenium (versión 4.x con Selenium Manager integrado)
================================================================================
"""

import re
import urllib.parse
from typing import Dict, List, Optional, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# [NOTA DOCENTE - DOMINIO OBJETIVO]:
BASE_URL = "https://cuevana3.town"

# [NOTA DOCENTE - PATRÓN SINGLETON PARA WEBDRIVER]:
# Crear una instancia de Chrome para cada clic en la terminal abriría y cerraría procesos
# del navegador continuamente, ralentizando el programa de forma crítica.
# Mantenemos una instancia global única reutilizable (Lazy Loading).
_driver_instance: Optional[webdriver.Chrome] = None


def obtener_driver() -> webdriver.Chrome:
    """
    [EXPLICACIÓN DOCENTE]:
    Inicializa el WebDriver de Chrome con opciones de rendimiento y anti-detección.
    En Selenium 4.6+, Selenium Manager descarga y administra automáticamente el
    binario de ChromeDriver compatible con la versión de Google Chrome del sistema.
    """
    global _driver_instance

    if _driver_instance is not None:
        try:
            # Comprobar si el navegador sigue vivo ejecutando un comando ligero
            _driver_instance.current_url
            return _driver_instance
        except Exception:
            _driver_instance = None

    chrome_options = Options()

    # 1. Modo Headless Moderno: ejecuta Chrome sin interfaz gráfica de usuario (GUI).
    chrome_options.add_argument("--headless=new")

    # 2. Optimizaciones de rendimiento: deshabilitar aceleración por GPU y Sandbox
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")

    # 3. Optimización crítica: deshabilitar la descarga de imágenes en el scraper
    # para acelerar la carga de páginas en un 400% y ahorrar ancho de banda.
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)

    # 4. Anti-Fingerprinting (Bypass de detección de bots):
    # Ocultar la bandera 'navigator.webdriver' que delata que Chrome está siendo automatizado.
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # 5. User-Agent realista
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )

    # Silenciar logs innecesarios de DevTools
    chrome_options.add_argument("--log-level=3")

    _driver_instance = webdriver.Chrome(options=chrome_options)
    _driver_instance.set_page_load_timeout(20)
    return _driver_instance


def cerrar_driver():
    """Cierra la sesión del navegador y libera los recursos de memoria del sistema."""
    global _driver_instance
    if _driver_instance:
        try:
            _driver_instance.quit()
        except Exception:
            pass
        _driver_instance = None


# ==============================================================================
# SECCIÓN 1: BÚSQUEDA MEDIANTE SELENIUM Y NAVEGACIÓN DOM
# ==============================================================================

def buscar_contenido(termino: str) -> List[Dict[str, Any]]:
    """
    [EXPLICACIÓN DOCENTE]:
    Navega a la URL de búsqueda y espera a que los elementos del catálogo se rendericen
    en el DOM mediante esperas explícitas (WebDriverWait).
    """
    driver = obtener_driver()
    url_busqueda = f"{BASE_URL}/?s={urllib.parse.quote_plus(termino)}"

    try:
        driver.get(url_busqueda)
        # [NOTA DOCENTE - ESPERAS EXPLÍCITAS]:
        # Esperamos hasta 8 segundos a que al menos un elemento enlace esté presente en el DOM.
        # Es mucho más robusto que usar `time.sleep()`.
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]'))
        )
    except Exception as err:
        # Si no encuentra elementos dentro del timeout, la búsqueda probablemente no arrojó resultados
        pass

    resultados: List[Dict[str, Any]] = []

    # Localizar todos los nodos <a> que apunten a películas o series
    elementos = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]')

    for el in elementos:
        try:
            href = el.get_attribute("href") or ""
            if not href or "/play/" in href or href.startswith("javascript:"):
                continue

            # Extraer el texto del título (Selenium evalúa textContents / innerText)
            titulo = el.text.strip()
            if not titulo:
                titulo = el.get_attribute("title") or ""

            # Si el elemento tiene un título multilínea, tomar la línea del nombre
            lineas = [l.strip() for l in titulo.split("\n") if l.strip()]
            titulo_limpio = lineas[-1] if lineas else titulo

            # Extraer póster (Selenium puede leer tanto 'data-src' como 'src')
            poster = None
            try:
                img = el.find_element(By.TAG_NAME, "img")
                poster = img.get_attribute("data-src") or img.get_attribute("src")
            except Exception:
                pass

            # Extraer año con expresiones regulares
            match_anio = re.search(r"[-_](\d{4})[-_]", href) or re.search(r"\b(19\d\d|20\d\d)\b", titulo)
            anio = int(match_anio.group(1)) if match_anio else None

            titulo_final = re.sub(r"\s*\(\d{4}\)\s*", "", titulo_limpio).strip()

            if titulo_final and not any(r["url"] == href for r in resultados):
                resultados.append({
                    "titulo": titulo_final,
                    "anio": anio,
                    "tipo": "tv" if "/serie/" in href else "movie",
                    "url": href,
                    "poster": poster
                })
        except Exception:
            continue

    return resultados


def listar_catalogo(categoria: str = "peliculas", pagina: int = 1) -> List[Dict[str, Any]]:
    """
    [EXPLICACIÓN DOCENTE]:
    Navega por las páginas del catálogo con Selenium:
    - Películas: /mejores-peliculas/page/{pagina}/
    - Populares: /peliculas-populares/page/{pagina}/
    - Estrenos: /nuevas-peliculas/page/{pagina}/
    - Series: /series/page/{pagina}/
    """
    driver = obtener_driver()

    slug_map = {
        "peliculas": "mejores-peliculas",
        "mejores": "mejores-peliculas",
        "populares": "peliculas-populares",
        "estrenos": "nuevas-peliculas",
        "nuevas": "nuevas-peliculas",
        "series": "series"
    }
    slug = slug_map.get(categoria.lower(), "mejores-peliculas")

    if pagina == 1:
        url = f"{BASE_URL}/{slug}/"
    else:
        url = f"{BASE_URL}/{slug}/page/{pagina}/"

    try:
        driver.get(url)
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]'))
        )
    except Exception:
        pass

    catalogo: List[Dict[str, Any]] = []
    elementos = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]')

    for el in elementos:
        try:
            href = el.get_attribute("href") or ""
            if not href or "/play/" in href or href.startswith("javascript:"):
                continue

            titulo = el.text.strip()
            lineas = [l.strip() for l in titulo.split("\n") if l.strip()]
            titulo_limpio = lineas[-1] if lineas else titulo

            poster = None
            try:
                img = el.find_element(By.TAG_NAME, "img")
                poster = img.get_attribute("data-src") or img.get_attribute("src")
            except Exception:
                pass

            match_anio = re.search(r"[-_](\d{4})[-_]", href) or re.search(r"\b(19\d\d|20\d\d)\b", titulo)
            anio = int(match_anio.group(1)) if match_anio else None

            titulo_final = re.sub(r"\s*\(\d{4}\)\s*", "", titulo_limpio).strip()

            if titulo_final and not any(c["url"] == href for c in catalogo):
                catalogo.append({
                    "titulo": titulo_final,
                    "anio": anio,
                    "tipo": "tv" if "/serie/" in href else "movie",
                    "url": href,
                    "poster": poster
                })
        except Exception:
            continue

    return catalogo


# ==============================================================================
# SECCIÓN 2: EXTRACCIÓN DE REPRODUCTORES Y STREAMS DE DURACIÓN COMPLETA
# ==============================================================================

def extraer_streams(url_detalle: str) -> List[Dict[str, str]]:
    """
    [EXPLICACIÓN DOCENTE]:
    1. Extrae el identificador de TMDB contenido en la estructura de la URL de Cuevana.
       Con este identificador se proporcionan streams de 2h a 3h completos.
    2. Utiliza Selenium para cargar la página `/play/` y analizar el código fuente
       renderizado por el motor de JavaScript (driver.page_source).
    """
    streams: List[Dict[str, str]] = []

    # 1. Extracción de ID de TMDB para películas completas (2h - 3h)
    match_pelicula = re.search(r"-c(\d+)v", url_detalle)
    match_serie = re.search(r"/serie/(\d+)(?:-(\d+)-(\d+))?", url_detalle)

    if match_pelicula:
        tmdb_id = match_pelicula.group(1)
        streams.append({
            "servidor": "SmashyStream HD (Película Completa 2h-3h)",
            "calidad": "1080p / 4K",
            "idioma": "Latino / Original / Sub",
            "tipo": "embed",
            "url": f"https://player.smashystream.com/movie/{tmdb_id}",
            "tmdb_id": tmdb_id,
            "nota": "Servidor limpio de alta fidelidad sin popunders ni redirecciones."
        })
        streams.append({
            "servidor": "VidSrc VIP (Película Completa)",
            "calidad": "HD 1080p",
            "idioma": "Audio Original / Doblado",
            "tipo": "embed",
            "url": f"https://vidsrc.me/embed/movie?tmdb={tmdb_id}",
            "tmdb_id": tmdb_id,
            "nota": "Servidor de alta velocidad."
        })
        streams.append({
            "servidor": "AutoEmbed HD (Película Completa)",
            "calidad": "HD 1080p",
            "idioma": "Latino / Original",
            "tipo": "embed",
            "url": f"https://autoembed.co/movie/tmdb/{tmdb_id}",
            "tmdb_id": tmdb_id,
            "nota": "Servidor alternativo de respaldo."
        })
    elif match_serie:
        show_id = match_serie.group(1)
        s = match_serie.group(2) or "1"
        e = match_serie.group(3) or "1"
        streams.append({
            "servidor": f"SmashyStream Serie (T{s}E{e} Completo)",
            "calidad": "HD",
            "idioma": "Latino / Sub",
            "tipo": "embed",
            "url": f"https://player.smashystream.com/tv/{show_id}?s={s}&e={e}",
            "nota": "Episodio completo de serie de TV sin anuncios."
        })
        streams.append({
            "servidor": f"VidSrc Serie (T{s}E{e} Completo)",
            "calidad": "HD",
            "idioma": "Latino / Original",
            "tipo": "embed",
            "url": f"https://vidsrc.me/embed/tv?tmdb={show_id}&sea={s}&epi={e}",
            "nota": "Episodio completo en VidSrc."
        })

    # 2. Navegar a /play/ con Selenium para extraer el stream directo mediante JavaScript
    play_url = url_detalle if url_detalle.endswith("/play/") else f"{url_detalle.rstrip('/')}/play/"

    driver = obtener_driver()
    try:
        driver.get(play_url)
        # Extraer el código fuente HTML resultante
        page_source = driver.page_source

        # Buscar el archivo de video inyectado en VideoJS mediante Regex
        match_src = re.search(
            r"player\.src\(\s*\{\s*src:\s*['\"]([^'\"]+)['\"](?:,\s*type:\s*['\"]([^'\"]+)['\"])?",
            page_source,
            re.IGNORECASE
        )
        if match_src:
            video_url = match_src.group(1)
            video_type = match_src.group(2) or "video/mp4"
            streams.append({
                "servidor": "Clip Directo Teaser (VideoJS)",
                "calidad": "HD (Clip Corto)",
                "idioma": "Latino",
                "tipo": video_type,
                "url": video_url,
                "nota": "Demostración de scraping regex en clase (Video teaser del sitio)."
            })

        # Buscar listas HLS (.m3u8)
        m3u8_matches = re.findall(r"https?://[^\s\"',;<>]+\.m3u8[^\s\"',;<>]*", page_source)
        for m_url in m3u8_matches:
            if not any(s["url"] == m_url for s in streams):
                streams.append({
                    "servidor": "HLS Adaptive Stream",
                    "calidad": "Auto (HLS)",
                    "idioma": "Latino / Original",
                    "tipo": "application/x-mpegURL",
                    "url": m_url,
                    "nota": "Stream de video completo HLS."
                })

        # Extraer iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for ifr in iframes:
            try:
                src = ifr.get_attribute("src") or ifr.get_attribute("data-src")
                if src and not any(ign in src for ign in ["google", "analytics", "ads"]):
                    streams.append({
                        "servidor": "Servidor Embebido (Iframe)",
                        "calidad": "HD",
                        "idioma": "Latino / Castellano",
                        "tipo": "embed",
                        "url": src,
                        "nota": "Reproductor web seguro encapsulado."
                    })
            except Exception:
                continue

    except Exception as err:
        print(f"[ERROR PROFESOR] Error en Selenium navegando a {play_url}: {err}")

    return streams


def resolver_episodio_serie(url_serie: str, temporada: int, episodio: int) -> Optional[str]:
    """
    [EXPLICACIÓN DOCENTE]:
    Localiza la URL del episodio utilizando Selenium y esperas de elementos.
    """
    driver = obtener_driver()
    try:
        match_id = re.search(r"/serie/(\d+)(?:-\d+)?/(.+)$", url_serie)
        url_temporada = url_serie
        if match_id:
            show_id, slug = match_id.group(1), match_id.group(2)
            url_temporada = f"{BASE_URL}/serie/{show_id}-{temporada}/{slug}"

        driver.get(url_temporada)
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.TAG_NAME, "a"))
        )

        patron = re.compile(rf"-{temporada}-{episodio}/")
        enlaces = driver.find_elements(By.TAG_NAME, "a")

        for a in enlaces:
            try:
                href = a.get_attribute("href") or ""
                if patron.search(href):
                    return href
            except Exception:
                continue

        return None
    except Exception as err:
        print(f"[ERROR PROFESOR] Error localizando episodio con Selenium: {err}")
        return None
