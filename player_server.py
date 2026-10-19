"""
================================================================================
SERVIDOR LOCAL FLIXQUEST — player_server.py
================================================================================
Este archivo contiene SOLO la lógica Python del servidor HTTP.
Todo el diseño visual (HTML, CSS, JS) está en player.html.

Flujo de trabajo:
  1. El CLI llama a abrir_en_navegador(titulo, url, tipo, tmdb_id)
  2. El servidor levanta en http://localhost:8080 (hilo daemon)
  3. Chrome abre /player?... → el servidor lee player.html,
     reemplaza los placeholders y devuelve la página completa
  4. El usuario elige un servidor → /launch?url=... → redirige directo al proveedor

Rutas disponibles:
  GET /player?title=&src=&type=&tmdb=   → Página de selección / reproductor
  GET /launch?url=&title=               → Página spinner → redirect al proveedor
================================================================================
"""

import http.server
import socketserver
import threading
import urllib.parse
import webbrowser
import os
import json
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────
PORT = 8080

# Rutas a los templates HTML (mismo directorio que este script)
_BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PLAYER = os.path.join(_BASE, "player.html")
TEMPLATE_LAUNCH = os.path.join(_BASE, "launch.html")

_server_instance: Optional[socketserver.TCPServer] = None
_server_thread:   Optional[threading.Thread]       = None


def _leer_html(ruta: str) -> str:
    """
    Lee un archivo HTML desde disco.
    Si no existe, devuelve una página de error básica.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "<!DOCTYPE html><html><body style='background:#090b10;color:#f87171;"
            "font-family:sans-serif;padding:2rem'>"
            f"<h2>⚠ No se encontró {os.path.basename(ruta)}</h2>"
            f"<p>Ruta esperada: {ruta}</p>"
            "</body></html>"
        )


def _renderizar(titulo: str, tipo_stream: str, contenido: str, script_player: str) -> str:
    """
    Carga player.html y reemplaza los 4 placeholders:
      {{TITULO}}        → nombre de la película / serie
      {{TIPO_STREAM}}   → etiqueta del badge (ej. "Película Completa HD")
      {{CONTENIDO}}     → bloque HTML central (tarjetas de servidor o <video>)
      {{SCRIPT_PLAYER}} → código JS específico del tipo de stream
    """
    html = _leer_html(TEMPLATE_PLAYER)
    html = html.replace("{{TITULO}}",        titulo)
    html = html.replace("{{TIPO_STREAM}}",   tipo_stream)
    html = html.replace("{{CONTENIDO}}",     contenido)
    html = html.replace("{{SCRIPT_PLAYER}}", script_player)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Bloques de contenido HTML según el tipo de stream
# ─────────────────────────────────────────────────────────────────────────────

def _html_tarjetas_servidor(tmdb_id: str, titulo_enc: str) -> str:
    """
    Genera el grid con las 3 tarjetas de servidor (embed / película completa).
    El usuario hace clic en una → va a /launch → redirige al proveedor real.
    """
    def enc(url):
        return urllib.parse.quote(url)

    smashy    = enc(f"https://player.smashystream.com/movie/{tmdb_id}")
    vidsrc    = enc(f"https://vidsrc.me/embed/movie?tmdb={tmdb_id}")
    autoembed = enc(f"https://autoembed.co/movie/tmdb/{tmdb_id}")

    return f"""
    <div class="info-box">
        <strong>Elige un servidor</strong> — Se abrirá en esta misma pestaña.<br>
        Chrome bloquea automáticamente los popups no iniciados por el usuario.
        Si un servidor no carga, prueba el siguiente.
    </div>

    <div class="server-grid">
        <a href="/launch?url={smashy}&title={titulo_enc}" class="server-card">
            <div class="icono">🎬</div>
            <div class="nombre">Servidor 1</div>
            <div class="calidad">SmashyStream · 1080p / 4K</div>
            <div class="nota">✓ Recomendado</div>
        </a>
        <a href="/launch?url={vidsrc}&title={titulo_enc}" class="server-card">
            <div class="icono">📺</div>
            <div class="nombre">Servidor 2</div>
            <div class="calidad">VidSrc VIP · HD 1080p</div>
            <div class="nota">✓ Alta velocidad</div>
        </a>
        <a href="/launch?url={autoembed}&title={titulo_enc}" class="server-card">
            <div class="icono">⚡</div>
            <div class="nombre">Servidor 3</div>
            <div class="calidad">AutoEmbed · HD</div>
            <div class="nota">✓ Respaldo</div>
        </a>
    </div>
    """


def _html_video(id_elem: str = "vp") -> str:
    """Elemento <video> para streams HLS y MP4 directos."""
    return f"""
    <div class="player-box">
        <video id="{id_elem}" class="video-js vjs-default-skin vjs-big-play-centered"
               controls autoplay playsinline preload="auto"></video>
    </div>
    """


def _js_hls(stream_url: str, id_elem: str = "vp") -> str:
    """Script HLS usando hls.js (cargado desde CDN en player.html)."""
    return f"""
    var video = document.getElementById('{id_elem}');
    var src   = {json.dumps(stream_url)};
    if (Hls.isSupported()) {{
        var hls = new Hls();
        hls.loadSource(src);
        hls.attachMedia(video);
        hls.on(Hls.Events.MANIFEST_PARSED, function() {{
            video.play().catch(function() {{}});
        }});
    }} else if (video.canPlayType('application/vnd.apple.mpegurl')) {{
        video.src = src;
    }}
    """


def _js_mp4(stream_url: str, id_elem: str = "vp") -> str:
    """Script para video MP4 directo."""
    return f"""
    var video = document.getElementById('{id_elem}');
    video.src = {json.dumps(stream_url)};
    video.play().catch(function() {{}});
    """


def _js_redirect(launch_path: str) -> str:
    """Redirección automática a /launch cuando no hay tmdb_id."""
    return f"setTimeout(function(){{ window.location.href = {json.dumps(launch_path)}; }}, 800);"


# ─────────────────────────────────────────────────────────────────────────────
# Página spinner para /launch — lee launch.html y reemplaza {{URL_DESTINO}}
# ─────────────────────────────────────────────────────────────────────────────
def _pagina_launch(target_url: str) -> str:
    """
    Lee launch.html, sustituye {{URL_DESTINO}} con la URL real del proveedor
    y devuelve el HTML completo de la pantalla de carga/spinner.

    Por qué funciona sin iframe ni proxy:
    - El proveedor se carga directamente en la pestaña del usuario.
    - Chrome bloquea window.open() automático → no hay popups.
    - sbx.js de vidsrc no puede detectar sandbox (no hay ninguno).
    """
    html = _leer_html(TEMPLATE_LAUNCH)
    html = html.replace("{{URL_DESTINO}}", target_url)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# Handler HTTP
# ─────────────────────────────────────────────────────────────────────────────
class PlayerRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query  = urllib.parse.parse_qs(parsed.query)

        # ── GET /launch?url=...&title=... ─────────────────────────────────
        if parsed.path == "/launch":
            target_url = query.get("url", [""])[0]
            if not target_url:
                self._respond(400, "text/plain", b"Falta parametro url")
                return
            self._respond(200, "text/html; charset=utf-8",
                          _pagina_launch(target_url).encode())
            return

        # ── GET /player?title=&src=&type=&tmdb= ───────────────────────────
        if parsed.path in ["/player", "/"]:
            titulo      = query.get("title", ["FlixQuest Player"])[0]
            stream_url  = query.get("src",   [""])[0]
            stream_type = query.get("type",  ["video/mp4"])[0]
            tmdb_id     = query.get("tmdb",  [""])[0]

            titulo_enc = urllib.parse.quote(titulo)
            is_hls   = ".m3u8" in stream_url or "mpegURL" in stream_type
            is_embed = (stream_type == "embed" or
                        any(p in stream_url for p in
                            ["smashystream", "vidsrc", "autoembed", "embed"]))

            # Caso 1: Embed con TMDB → mostrar tarjetas de servidor
            if is_embed and tmdb_id:
                contenido     = _html_tarjetas_servidor(tmdb_id, titulo_enc)
                script_player = ""   # No hay video local; el JS del shield está en player.html
                tipo_stream   = "Película Completa HD"

            # Caso 2: Embed sin TMDB → redirigir directo
            elif is_embed:
                launch_path   = f"/launch?url={urllib.parse.quote(stream_url)}&title={titulo_enc}"
                contenido     = f'<div class="info-box"><strong>Redirigiendo...</strong></div>'
                script_player = _js_redirect(launch_path)
                tipo_stream   = "Embed HD"

            # Caso 3: Stream HLS (.m3u8)
            elif is_hls:
                contenido     = _html_video()
                script_player = _js_hls(stream_url)
                tipo_stream   = "HLS Streaming"

            # Caso 4: Video MP4 directo
            else:
                contenido     = _html_video()
                script_player = _js_mp4(stream_url)
                tipo_stream   = "Video Directo MP4"

            html = _renderizar(titulo, tipo_stream, contenido, script_player)
            self._respond(200, "text/html; charset=utf-8", html.encode())
            return

        self._respond(404, "text/plain", b"Not found")

    def _respond(self, code: int, content_type: str, body: bytes):
        self.send_response(code)
        self.send_header("Content-Type",   content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control",  "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Silenciar logs del servidor en la consola del CLI


# ─────────────────────────────────────────────────────────────────────────────
# API pública (usada por cli.py)
# ─────────────────────────────────────────────────────────────────────────────
def iniciar_servidor_reproductor(puerto: int = PORT) -> str:
    """Levanta el servidor HTTP en un hilo daemon. Idempotente."""
    global _server_instance, _server_thread
    if _server_instance is not None:
        return f"http://localhost:{puerto}"

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    _server_instance = ReusableTCPServer(("127.0.0.1", puerto), PlayerRequestHandler)
    _server_thread   = threading.Thread(
        target=_server_instance.serve_forever, daemon=True
    )
    _server_thread.start()
    return f"http://localhost:{puerto}"


def abrir_en_navegador(
    titulo:      str,
    stream_url:  str,
    stream_type: str = "video/mp4",
    tmdb_id:     str = "",
    puerto:      int = PORT,
) -> str:
    """Inicia el servidor y abre el reproductor en el navegador por defecto."""
    iniciar_servidor_reproductor(puerto)
    params = {"title": titulo, "src": stream_url, "type": stream_type}
    if tmdb_id:
        params["tmdb"] = tmdb_id
    url_final = f"http://localhost:{puerto}/player?{urllib.parse.urlencode(params)}"
    webbrowser.open(url_final)
    return url_final


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución directa (prueba rápida)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[FlixQuest] Servidor en http://localhost:{PORT}")
    print(f"[FlixQuest] Template: {TEMPLATE_PATH}")
    iniciar_servidor_reproductor(PORT)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("[FlixQuest] Servidor detenido.")
