"""
================================================================================
FLIXQUEST CUEVANA - CONSOLA INTERACTIVA EDUCATIVA EN PYTHON
Navegación de Catálogo, Búsquedas, Streaming HLS en Navegador y Descargas
================================================================================
"""

import sys
import os
from colorama import init, Fore, Style

# Importar funciones del scraper del profesor
from cuevana_scraper_profesor import (
    buscar_contenido,
    listar_catalogo,
    extraer_streams,
    resolver_episodio_serie,
    cerrar_driver
)
from player_server import abrir_en_navegador
from downloader import descargar_video

init(autoreset=True)


def banner():
    print(Fore.CYAN + Style.BRIGHT + """
  ╔═══════════════════════════════════════════════════════════════════════╗
  ║   🎬 FLIXQUEST CUEVANA - PYTHON SCRAPING & STREAMING TERMINAL UI      ║
  ║         Curso Educativo de Web Scraping y Extracción Multimedia       ║
  ╚═══════════════════════════════════════════════════════════════════════╝
    """)


def menu_principal():
    print(Fore.YELLOW + Style.BRIGHT + "--- MENÚ PRINCIPAL ---")
    print(f" {Fore.GREEN}[1]{Fore.RESET} 🔍 Buscar película o serie por título")
    print(f" {Fore.GREEN}[2]{Fore.RESET} 🎬 Explorar Catálogo de Películas (Paginado)")
    print(f" {Fore.GREEN}[3]{Fore.RESET} ✨ Explorar Estrenos Recientes")
    print(f" {Fore.GREEN}[4]{Fore.RESET} 📺 Explorar Catálogo de Series TV")
    print(f" {Fore.GREEN}[5]{Fore.RESET} 📖 Explicación Técnica: ¿Por qué duran poco los videos?")
    print(f" {Fore.RED}[0]{Fore.RESET} 🚪 Salir")
    print("-" * 50)


def mostrar_lista_elementos(items, titulo_seccion="Resultados"):
    print(f"\n{Fore.CYAN + Style.BRIGHT}=== {titulo_seccion} ({len(items)} items) ==={Fore.RESET}")
    if not items:
        print(Fore.RED + "No se encontraron elementos.")
        return None

    for i, item in enumerate(items, 1):
        badge = f"{Fore.BLUE}[SERIE]{Fore.RESET}" if item.get("tipo") == "tv" else f"{Fore.MAGENTA}[PELI]{Fore.RESET}"
        anio = f"({item['anio']})" if item.get("anio") else ""
        print(f"  {Fore.YELLOW}{i:2d}.{Fore.RESET} {badge} {Style.BRIGHT}{item['titulo']}{Style.RESET_ALL} {Fore.WHITE}{anio}")

    print(f"   {Fore.RED}0.{Fore.RESET} ↩ Cancelar / Volver")
    
    while True:
        opc = input(Fore.GREEN + "\nSelecciona el número a reproducir o descargar: " + Fore.RESET).strip()
        if opc == "0":
            return None
        if opc.isdigit() and 1 <= int(opc) <= len(items):
            return items[int(opc) - 1]
        print(Fore.RED + "Opción inválida. Intenta nuevamente.")


def gestionar_reproduccion_y_descarga(item):
    titulo = item["titulo"]
    url = item["url"]
    tipo = item.get("tipo", "movie")

    print(f"\n{Fore.CYAN + Style.BRIGHT}==========================================")
    print(f"  Seleccionado: {Style.BRIGHT}{titulo}{Style.RESET_ALL}")
    print(f"  Tipo: {'Serie de TV' if tipo == 'tv' else 'Película'}")
    print(f"  URL Base: {url}")
    print("==========================================" + Fore.RESET)

    target_play_url = url
    if tipo == "tv":
        try:
            temporada = int(input(Fore.YELLOW + "Introduce el número de Temporada [default 1]: " + Fore.RESET) or "1")
            episodio = int(input(Fore.YELLOW + "Introduce el número de Episodio [default 1]: " + Fore.RESET) or "1")
        except ValueError:
            temporada, episodio = 1, 1

        print(Fore.BLUE + f"[*] Buscando Episodio Temporada {temporada}, Episodio {episodio}..." + Fore.RESET)
        ep_url = resolver_episodio_serie(url, temporada, episodio)
        if not ep_url:
            print(Fore.RED + f"[!] No se encontró el episodio S{temporada}E{episodio} para esta serie.")
            return
        target_play_url = ep_url
        titulo = f"{titulo} (T{temporada}E{episodio})"

    print(Fore.BLUE + f"[*] Extrayendo streams y reproductores de: {target_play_url}..." + Fore.RESET)
    streams = extraer_streams(target_play_url)

    if not streams:
        print(Fore.RED + "[!] No se encontraron servidores de video activos para este contenido.")
        return

    print(f"\n{Fore.GREEN + Style.BRIGHT}Streams encontrados ({len(streams)}):{Fore.RESET}")
    for idx, s in enumerate(streams, 1):
        print(f"  [{idx}] {Style.BRIGHT}{s['servidor']}{Style.RESET_ALL} - Calidad: {s['calidad']} - Idioma: {s['idioma']}")
        print(f"      Tipo: {s['tipo']} | URL: {s['url'][:75]}...")

    while True:
        print(Fore.YELLOW + "\n¿Qué deseas hacer?" + Fore.RESET)
        print(f"  {Fore.GREEN}[V]{Fore.RESET}er en navegador (Abre Google Chrome con reproductor HLS / VideoJS)")
        print(f"  {Fore.CYAN}[D]{Fore.RESET}escargar video al PC local")
        print(f"  {Fore.RED}[R]{Fore.RESET}egresar al menú")
        accion = input(Fore.GREEN + "Opción (V/D/R): " + Fore.RESET).strip().upper()

        if accion == "R":
            break
        elif accion in ["V", "D"]:
            stream_idx = 0
            if len(streams) > 1:
                eleccion = input(f"Selecciona el número de stream [1-{len(streams)}, default 1]: ").strip()
                if eleccion.isdigit() and 1 <= int(eleccion) <= len(streams):
                    stream_idx = int(eleccion) - 1

            stream_elegido = streams[stream_idx]

            if accion == "V":
                print(Fore.CYAN + f"\n[*] Levantando servidor local y abriendo Google Chrome para: {titulo}..." + Fore.RESET)
                url_web = abrir_en_navegador(
                    titulo=titulo,
                    stream_url=stream_elegido["url"],
                    stream_type=stream_elegido["tipo"],
                    tmdb_id=stream_elegido.get("tmdb_id", "")
                )
                print(Fore.GREEN + f"[✓] ¡Abierto en el navegador! -> {url_web}")
            elif accion == "D":
                if stream_elegido["tipo"] == "embed":
                    print(Fore.YELLOW + "[!] Este servidor es un iframe embebido web. Descarga no disponible directamente para iframes.")
                    print(f"    Puedes abrirlo en navegador seleccionando [V].")
                else:
                    descargar_video(stream_elegido["url"], titulo)
            break


def loop_catalogo(categoria="peliculas", nombre="Películas"):
    pagina = 1
    while True:
        print(Fore.BLUE + f"\n[*] Cargando catálogo de {nombre} (Página {pagina})..." + Fore.RESET)
        items = listar_catalogo(categoria=categoria, pagina=pagina)
        
        print(f"\n{Fore.CYAN + Style.BRIGHT}=== {nombre.upper()} - PÁGINA {pagina} ({len(items)} items) ==={Fore.RESET}")
        for i, item in enumerate(items, 1):
            badge = f"{Fore.BLUE}[SERIE]{Fore.RESET}" if item.get("tipo") == "tv" else f"{Fore.MAGENTA}[PELI]{Fore.RESET}"
            anio = f"({item['anio']})" if item.get("anio") else ""
            print(f"  {Fore.YELLOW}{i:2d}.{Fore.RESET} {badge} {Style.BRIGHT}{item['titulo']}{Style.RESET_ALL} {Fore.WHITE}{anio}")

        print("\nOpciones de navegación:")
        print(f"  {Fore.GREEN}[1-{len(items)}]{Fore.RESET}: Seleccionar contenido")
        print(f"  {Fore.CYAN}[S]{Fore.RESET}: Página Siguiente")
        if pagina > 1:
            print(f"  {Fore.CYAN}[A]{Fore.RESET}: Página Anterior")
        print(f"  {Fore.RED}[M]{Fore.RESET}: Volver al Menú Principal")

        opc = input(Fore.GREEN + "Elige una opción: " + Fore.RESET).strip().upper()
        if opc == "M":
            break
        elif opc == "S":
            pagina += 1
        elif opc == "A" and pagina > 1:
            pagina -= 1
        elif opc.isdigit() and 1 <= int(opc) <= len(items):
            gestionar_reproduccion_y_descarga(items[int(opc) - 1])
            break


def mostrar_explicacion_docente():
    print(Fore.YELLOW + Style.BRIGHT + "\n=== EXPLICACIÓN TÉCNICA PEDAGÓGICA (PARA PROFESORES Y ALUMNOS) ===")
    print(Fore.WHITE + """
1. ¿POR QUÉ LOS VIDEOS DE CUEVANA A VECES DURAN TAN POCO (~10-15 SEGUNDOS)?
   - En sitios como cuevana3.town, el script embebido en la página es:
     `player.src({ src: 'https://vids.vidplayz.site/.../m4rv3l.mp4', type: 'video/mp4' });`
     `pausetime = 10;`
     `myPlayer.on("timeupdate", function() { if (currentTime >= pausetime) pause(); modal(); });`
     `player.duration = function() { return 6700; };`

   - Fíjate en el engaño: usan Video.js para falsear la duración visible en 6700 segundos (1h 51m),
     pero el archivo físico descargado pesa solo ~7.5 MB (un teaser de 15 segundos). Al llegar al segundo 10,
     el evento JavaScript 'timeupdate' detiene el video y despliega una ventana emergente que exige
     registrarse para ver la versión completa.

2. ¿CÓMO LO SOLUCIONA EL SCRAPING EN PYTHON?
   - Nuestro scraper extrae el enlace limpio y remueve el script 'pausetime' para que no corte.
   - Además, rastrea las listas de reproducción maestras HTTP Live Streaming (HLS .m3u8) y los
     servidores iframes no restringidos, permitiendo reproducir o descargar sin ventanas trampa.

3. ¿POR QUÉ ANTES SOLO VEÍAMOS ESTRENOS?
   - Porque la URL base (`/`) o sin paginación devuelve únicamente el carrusel de novedades.
   - Al implementar la función `listar_catalogo(categoria, pagina)` podemos navegar a
     `/peliculas/page/2/`, `/estrenos/page/3/`, etc., obteniendo la totalidad de la base de datos.
    """)
    input(Fore.CYAN + "Presiona ENTER para regresar al menú..." + Fore.RESET)


def main():
    while True:
        banner()
        menu_principal()
        opcion = input(Fore.GREEN + "Elige una opción [0-5]: " + Fore.RESET).strip()

        if opcion == "1":
            query = input(Fore.YELLOW + "\nIntroduce el título de la película o serie: " + Fore.RESET).strip()
            if query:
                print(Fore.BLUE + f"[*] Buscando '{query}' en Cuevana..." + Fore.RESET)
                resultados = buscar_contenido(query)
                elegido = mostrar_lista_elementos(resultados, f"Resultados para '{query}'")
                if elegido:
                    gestionar_reproduccion_y_descarga(elegido)
        elif opcion == "2":
            loop_catalogo(categoria="peliculas", nombre="Películas")
        elif opcion == "3":
            loop_catalogo(categoria="estrenos", nombre="Estrenos Recientes")
        elif opcion == "4":
            loop_catalogo(categoria="series", nombre="Series de TV")
        elif opcion == "5":
            mostrar_explicacion_docente()
        elif opcion == "0":
            print(Fore.GREEN + "\n¡Gracias por usar FlixQuest Educativo! Hasta pronto.\n")
            break
        else:
            print(Fore.RED + "\nOpción no válida. Por favor elige un número del menú.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario. Saliendo...")
    finally:
        cerrar_driver()
