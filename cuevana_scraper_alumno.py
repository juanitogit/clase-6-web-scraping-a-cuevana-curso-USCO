"""
================================================================================
GUÍA DEL ALUMNO: WEB SCRAPING CON SELENIUM EN PYTHON
PROYECTO: BUSCADOR Y REPRODUCTOR DE STREAMING (CUEVANA)
================================================================================
Instrucciones:
En este módulo usamos Selenium WebDriver:
  1. Iniciamos Chrome en segundo plano (--headless).
  2. Navegamos a la página con driver.get().
  3. Esperamos y encontramos elementos con driver.find_elements(By.CSS_SELECTOR).
  4. Extraemos el título, año y enlaces con get_attribute().
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

# Dominio base
BASE_URL = "https://cuevana3.town"

# Variable para reutilizar la misma ventana de Chrome y que sea más rápido
_driver_alumno: Optional[webdriver.Chrome] = None


# PASO 1: CONFIGURAR E INICIAR EL NAVEGADOR CHROME
def obtener_driver() -> webdriver.Chrome:
    """
    Inicia Google Chrome en modo oculto (headless) con optimizaciones básicas.
    """
    global _driver_alumno

    if _driver_alumno is not None:
        try:
            _driver_alumno.current_url
            return _driver_alumno
        except Exception:
            _driver_alumno = None

    opciones = Options()
    opciones.add_argument("--headless=new")      # Sin ventana gráfica visible
    opciones.add_argument("--disable-gpu")        # Deshabilitar GPU para ahorrar recursos
    opciones.add_argument("--no-sandbox")
    opciones.add_argument("--log-level=3")        # Silenciar mensajes de Chrome

    # Acelerar la carga desactivando la descarga de imágenes
    prefs = {"profile.managed_default_content_settings.images": 2}
    opciones.add_experimental_option("prefs", prefs)

    _driver_alumno = webdriver.Chrome(options=opciones)
    _driver_alumno.set_page_load_timeout(20)
    return _driver_alumno


def cerrar_driver():
    """Cierra Chrome al terminar el programa."""
    global _driver_alumno
    if _driver_alumno:
        try:
            _driver_alumno.quit()
        except Exception:
            pass
        _driver_alumno = None


# PASO 2: BUSCAR CONTENIDO CON SELENIUM
def buscar_contenido(termino: str) -> List[Dict[str, Any]]:
    """
    Busca películas y series usando la barra de búsqueda de Cuevana con Selenium.
    """
    driver = obtener_driver()
    url = f"{BASE_URL}/?s={urllib.parse.quote_plus(termino)}"

    try:
        # Abrir la URL en el navegador
        driver.get(url)
        # Esperar hasta 8 segundos a que aparezcan los resultados en pantalla
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]'))
        )
    except Exception:
        pass

    resultados = []
    # Encontrar todos los enlaces de películas o series
    elementos = driver.find_elements(By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]')

    for el in elementos:
        try:
            href = el.get_attribute("href") or ""
            if not href or "/play/" in href or href.startswith("javascript:"):
                continue

            # Obtener el título del texto del elemento
            titulo = el.text.strip()
            lineas = [l.strip() for l in titulo.split("\n") if l.strip()]
            titulo_limpio = lineas[-1] if lineas else titulo

            # Obtener el póster si existe
            poster = None
            try:
                img = el.find_element(By.TAG_NAME, "img")
                poster = img.get_attribute("data-src") or img.get_attribute("src")
            except Exception:
                pass

            # Detectar el año
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


# PASO 3: EXPLORAR EL CATÁLOGO PAGINADO CON SELENIUM
def listar_catalogo(categoria: str = "peliculas", pagina: int = 1) -> List[Dict[str, Any]]:
    """
    Recorre las páginas del catálogo para ver películas completas y no solo estrenos.
    """
    driver = obtener_driver()

    slugs = {
        "peliculas": "mejores-peliculas",
        "populares": "peliculas-populares",
        "estrenos": "nuevas-peliculas",
        "series": "series"
    }
    slug = slugs.get(categoria.lower(), "mejores-peliculas")

    url = f"{BASE_URL}/{slug}/" if pagina == 1 else f"{BASE_URL}/{slug}/page/{pagina}/"

    try:
        driver.get(url)
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href*="/peliculas/"], a[href*="/serie/"]'))
        )
    except Exception:
        pass

    catalogo = []
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


# PASO 4: EXTRAER SERVIDORES Y REPRODUCTORES COMPLETOS
def extraer_streams(url_detalle: str) -> List[Dict[str, str]]:
    """
    Extrae reproductores de duración completa (2h a 3h) usando el identificador de TMDB,
    y extrae el reproductor directo de VideoJS cargado con Selenium.
    """
    streams = []

    # 1. Identificar ID de TMDB para películas completas
    match_pelicula = re.search(r"-c(\d+)v", url_detalle)
    match_serie = re.search(r"/serie/(\d+)(?:-(\d+)-(\d+))?", url_detalle)

    if match_pelicula:
        tmdb_id = match_pelicula.group(1)
        streams.append({
            "servidor": "SmashyStream HD (Película Completa 2h-3h)",
            "calidad": "1080p",
            "idioma": "Latino / Original / Sub",
            "tipo": "embed",
            "url": f"https://player.smashystream.com/movie/{tmdb_id}",
            "tmdb_id": tmdb_id
        })
        streams.append({
            "servidor": "VidSrc VIP (Película Completa)",
            "calidad": "HD",
            "idioma": "Latino / Original",
            "tipo": "embed",
            "url": f"https://vidsrc.me/embed/movie?tmdb={tmdb_id}",
            "tmdb_id": tmdb_id
        })
        streams.append({
            "servidor": "AutoEmbed HD (Película Completa)",
            "calidad": "HD",
            "idioma": "Latino / Original",
            "tipo": "embed",
            "url": f"https://autoembed.co/movie/tmdb/{tmdb_id}",
            "tmdb_id": tmdb_id
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
            "url": f"https://player.smashystream.com/tv/{show_id}?s={s}&e={e}"
        })

    # 2. Cargar página /play/ con Selenium para extraer el video JavaScript
    play_url = url_detalle if url_detalle.endswith("/play/") else f"{url_detalle.rstrip('/')}/play/"

    driver = obtener_driver()
    try:
        driver.get(play_url)
        codigo_fuente = driver.page_source

        # Buscar player.src({...})
        match_src = re.search(
            r"player\.src\(\s*\{\s*src:\s*['\"]([^'\"]+)['\"](?:,\s*type:\s*['\"]([^'\"]+)['\"])?",
            codigo_fuente,
            re.IGNORECASE
        )
        if match_src:
            streams.append({
                "servidor": "Clip Directo Teaser (VideoJS)",
                "calidad": "HD (Muestra)",
                "idioma": "Latino",
                "tipo": match_src.group(2) or "video/mp4",
                "url": match_src.group(1)
            })
    except Exception as e:
        print(f"Error cargando reproductor en Selenium: {e}")

    return streams


# PASO 5: LOCALIZAR EPISODIOS DE SERIES
def resolver_episodio_serie(url_serie: str, temporada: int, episodio: int) -> Optional[str]:
    """
    Navega a la serie y encuentra el enlace del episodio exacto con Selenium.
    """
    driver = obtener_driver()
    try:
        match_id = re.search(r"/serie/(\d+)(?:-\d+)?/(.+)$", url_serie)
        url_temporada = url_serie
        if match_id:
            show_id, slug = match_id.group(1), match_id.group(2)
            url_temporada = f"{BASE_URL}/serie/{show_id}-{temporada}/{slug}"

        driver.get(url_temporada)
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
    except Exception as e:
        print(f"Error buscando episodio en Selenium: {e}")
        return None
