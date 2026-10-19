"""
================================================================================
MÓDULO DE DESCARGA LOCAL DE VIDEOS EN PYTHON
Descarga streams MP4 directamente al almacenamiento del PC del estudiante
con barra de progreso en tiempo real y cálculo de velocidad.
================================================================================
"""

import os
import re
import sys
import time
import requests

DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://cuevana3.town/"
}


def sanitizar_nombre_archivo(nombre: str) -> str:
    """
    Elimina caracteres prohibidos en sistemas de archivos (Windows, Linux, macOS)
    """
    nombre_limpio = re.sub(r'[\\/*?:"<>|]', "", nombre)
    return nombre_limpio.strip()


def descargar_video(url: str, titulo: str) -> bool:
    """
    Descarga el archivo multimedia con barra de progreso en la consola.
    """
    if not os.path.exists(DOWNLOADS_DIR):
        os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    extension = ".mp4"
    if ".m3u8" in url:
        extension = ".m3u8"

    nombre_archivo = f"{sanitizar_nombre_archivo(titulo)}{extension}"
    ruta_destino = os.path.join(DOWNLOADS_DIR, nombre_archivo)

    print(f"\n[+] Iniciando descarga de: {titulo}")
    print(f"[+] Destino: {ruta_destino}")

    try:
        inicio = time.time()
        with requests.get(url, headers=HEADERS, stream=True, timeout=15) as r:
            r.raise_for_status()
            total_length = r.headers.get("content-length")

            with open(ruta_destino, "wb") as f:
                if total_length is None:
                    # Sin tamaño fijo en cabecera
                    f.write(r.content)
                    print("[✓] Descarga completa (tamaño desconocido).")
                    return True
                else:
                    dl = 0
                    total_length = int(total_length)
                    total_mb = total_length / (1024 * 1024)
                    chunk_size = 1024 * 64  # 64 KB por bloque

                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        dl += len(chunk)
                        f.write(chunk)

                        done = int(50 * dl / total_length)
                        dl_mb = dl / (1024 * 1024)
                        porcentaje = (dl / total_length) * 100
                        barra = "█" * done + "░" * (50 - done)

                        sys.stdout.write(
                            f"\r[{barra}] {porcentaje:5.1f}% ({dl_mb:6.2f} / {total_mb:6.2f} MB)"
                        )
                        sys.stdout.flush()

        segundos = max(1, int(time.time() - inicio))
        print(f"\n[✓] ¡Descarga exitosa en {segundos}s! Guardado en:")
        print(f"    -> {ruta_destino}\n")
        return True

    except Exception as e:
        print(f"\n[!] Error durante la descarga: {e}")
        return False
