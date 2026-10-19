<div align="center">

<svg width="72" height="72" viewBox="0 0 72 72" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="72" height="72" rx="16" fill="#0f172a"/>
  <rect x="14" y="20" width="44" height="32" rx="4" fill="none" stroke="#4f46e5" stroke-width="2.5"/>
  <circle cx="36" cy="36" r="8" fill="#4f46e5"/>
  <polygon points="33,32 33,40 41,36" fill="#fff"/>
  <rect x="28" y="56" width="16" height="3" rx="1.5" fill="#334155"/>
  <rect x="34" y="52" width="4" height="5" rx="1" fill="#334155"/>
</svg>

# FlixQuest — Curso de Web Scraping con Python y Selenium

<img src="https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"/>
<img src="https://img.shields.io/badge/Selenium-4.x-43b02a?style=flat-square&logo=selenium&logoColor=white" alt="Selenium 4"/>
<img src="https://img.shields.io/badge/Nivel-Intermedio-f59e0b?style=flat-square" alt="Nivel intermedio"/>

</div>

---

## Descripcion

Este repositorio forma parte de un curso practico de **web scraping con Python y Selenium**. El proyecto extrae informacion del catalogo de Cuevana, construye una interfaz de navegacion en la terminal y abre un reproductor local en el navegador para ver el contenido completo.

El objetivo no es el sitio en si, sino aprender las tecnicas reales que se usan en scraping profesional: navegadores sin cabeza, espera de elementos dinamicos, expresiones regulares, servidores HTTP locales y manejo de restricciones de seguridad del navegador.

---

## Estructura del proyecto

```
FlixQuest-Python-Cuevana/
|
+-- cli.py                  Interfaz de terminal: menu, paginacion, busqueda
+-- scraper.py              Scraper con Selenium: extrae catalogo y streams de Cuevana
+-- downloader.py           Descargador de video con barra de progreso
+-- player_server.py        Servidor HTTP local (lee player.html y launch.html)
+-- player.html             Pagina del selector de servidores (CSS + HTML + JS)
+-- launch.html             Pantalla de transicion antes de abrir el proveedor
+-- ejecutar_cli.bat        Lanzador de Windows (doble clic para iniciar)
+-- downloads/              Carpeta donde se guardan los videos descargados
```

---

## Requisitos previos

| Requisito | Version minima | Verificacion |
|-----------|---------------|--------------|
| Python | 3.10 | `python --version` |
| Google Chrome | Cualquier version reciente | Instalado en el sistema |
| ChromeDriver | Debe coincidir con Chrome | Se instala automaticamente con `selenium` 4.x |
| pip | Incluido con Python | `pip --version` |

---

## Instalacion

### 1. Clonar el repositorio

Abre una terminal (CMD o PowerShell en Windows) y ejecuta:

```bash
git clone https://github.com/juanitogit/clase-6-web-scraping-a-cuevana-curso-USCO.git
cd clase-6-web-scraping-a-cuevana-curso-USCO
```

### 2. Crear un entorno virtual (recomendado)

Un entorno virtual aisla las dependencias de este proyecto del resto del sistema:

```bash
python -m venv venv
```

Activarlo en Windows:

```bash
venv\Scripts\activate
```

Activarlo en Mac / Linux:

```bash
source venv/bin/activate
```

Cuando el entorno este activo veras `(venv)` al inicio de la linea en la terminal.

### 3. Instalar dependencias

```bash
pip install selenium requests colorama
```

| Libreria | Para que se usa |
|----------|----------------|
| `selenium` | Controlar Chrome para navegar paginas con JavaScript dinamico |
| `requests` | Hacer peticiones HTTP simples (descarga de video) |
| `colorama` | Colores en la terminal en Windows |

### 4. Ejecutar el proyecto

**Opcion A — Doble clic:**

Abre `ejecutar_cli.bat` desde el explorador de archivos.

**Opcion B — Terminal:**

```bash
python cli.py
```

---

## Como funciona el codigo

El proyecto esta dividido en capas con responsabilidades separadas:

### Capa 1 — Scraping (`scraper.py`)

Selenium abre Chrome en modo sin cabeza (invisible) y navega a Cuevana. Dado que el sitio carga su catalogo con JavaScript de forma dinamica, se usa `WebDriverWait` para esperar a que los elementos aparezcan en el DOM antes de leerlos.

Cada pelicula en el catalogo contiene en su URL un identificador de TMDB (The Movie Database). Este identificador se extrae con una expresion regular y se usa para consultar proveedores que tienen el contenido completo.

```
URL de Cuevana:  /peliculas/avengers-endgame-c299534v/
                                              ^^^^^^
                                        TMDB ID = 299534
```

### Capa 2 — Interfaz de terminal (`cli.py`)

Muestra un menu interactivo con opciones de catalogo, busqueda y paginacion. Cuando el usuario selecciona una pelicula puede elegir verla en el navegador o descargarla al disco.

### Capa 3 — Servidor local (`player_server.py` + `player.html` + `launch.html`)

Se levanta un servidor HTTP en `http://localhost:8080`. Cuando el usuario elige ver una pelicula, el servidor lee `player.html`, reemplaza los valores dinamicos (titulo, tipo de stream) y envia la pagina al navegador.

El usuario elige un servidor de streaming en la pantalla de seleccion. Al hacer clic, el servidor sirve `launch.html` con la URL del proveedor inyectada, que muestra un spinner breve y luego redirige directamente al proveedor en la misma pestana.

### Capa 4 — Descarga (`downloader.py`)

Descarga el video en fragmentos de 8 KB en lugar de cargarlo todo en memoria. Muestra una barra de progreso en la terminal y guarda el archivo en la carpeta `downloads/`.

---

## Preguntas frecuentes

**El navegador no abre o da error de ChromeDriver**

Asegurate de tener Google Chrome instalado. Selenium 4.x descarga ChromeDriver automaticamente si no encuentra uno compatible. Si persiste el error, ejecuta:

```bash
pip install --upgrade selenium
```

**La terminal muestra "No se encontraron resultados"**

El sitio puede haber cambiado su estructura HTML. Avisa al profesor para actualizar el selector CSS en el scraper.

**El video no carga en el reproductor**

Prueba los otros servidores usando los botones de la pantalla de seleccion. Si ninguno carga, el contenido puede no estar disponible en ese momento.

**Donde quedan los videos descargados**

En la carpeta `downloads/` dentro del proyecto.

---

## Referencia rapida de comandos

```bash
# Clonar el repositorio
git clone https://github.com/juanitogit/clase-6-web-scraping-a-cuevana-curso-USCO.git

# Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac / Linux

# Instalar dependencias
pip install selenium requests colorama

# Iniciar la aplicacion
python cli.py
```
