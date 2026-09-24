"""
Lógica principal de PDF Toolkit.

Aquí solo hay funciones "puras": reciben rutas de archivos y parámetros,
hacen la operación y devuelven las rutas de los archivos creados.
No saben nada de ventanas ni botones; así se pueden probar con tests
y reutilizar desde cualquier interfaz (escritorio, terminal, web...).
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable, Sequence

import img2pdf
import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

# Formatos de imagen que aceptamos para convertir a PDF
FORMATOS_IMAGEN = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


class PdfToolError(Exception):
    """Error 'amigable' que la interfaz puede mostrar directamente al usuario."""


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _comprobar_existe(ruta: str | Path) -> Path:
    ruta = Path(ruta)
    if not ruta.is_file():
        raise PdfToolError(f"No se encuentra el archivo: {ruta}")
    return ruta


def _abrir_pdf(ruta: str | Path) -> PdfReader:
    ruta = _comprobar_existe(ruta)
    try:
        lector = PdfReader(ruta)
    except Exception as e:  # pypdf lanza varios tipos de error distintos
        raise PdfToolError(f"No se puede leer '{ruta.name}' como PDF: {e}") from e
    if lector.is_encrypted:
        raise PdfToolError(f"'{ruta.name}' está protegido con contraseña.")
    return lector


def contar_paginas(ruta: str | Path) -> int:
    """Devuelve el número de páginas de un PDF."""
    return len(_abrir_pdf(ruta).pages)


def parsear_rangos(texto: str, total_paginas: int) -> list[list[int]]:
    """
    Convierte un texto como "1-3, 5, 8-10" en una lista de grupos de páginas.

    Las páginas se escriben empezando en 1 (como las ve una persona),
    pero se devuelven empezando en 0 (como las usa Python).

    >>> parsear_rangos("1-3, 5", 10)
    [[0, 1, 2], [4]]
    """
    grupos: list[list[int]] = []
    for trozo in texto.replace(";", ",").split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        try:
            if "-" in trozo:
                inicio_txt, fin_txt = trozo.split("-", 1)
                inicio = int(inicio_txt)
                # "5-" significa "de la 5 hasta el final"
                fin = int(fin_txt) if fin_txt.strip() else total_paginas
            else:
                inicio = fin = int(trozo)
        except ValueError:
            raise PdfToolError(f"Rango no válido: '{trozo}'. Usa algo como 1-3, 5, 8-")

        if inicio < 1 or fin > total_paginas or inicio > fin:
            raise PdfToolError(
                f"El rango '{trozo}' no es válido: el documento tiene {total_paginas} páginas."
            )
        grupos.append(list(range(inicio - 1, fin)))

    if not grupos:
        raise PdfToolError("No has indicado ninguna página.")
    return grupos


# --------------------------------------------------------------------------- #
# Operaciones
# --------------------------------------------------------------------------- #
def unir_pdfs(rutas: Sequence[str | Path], salida: str | Path) -> Path:
    """Une varios PDFs, en el orden recibido, en un único archivo."""
    if len(rutas) < 2:
        raise PdfToolError("Necesitas al menos dos PDFs para unir.")

    escritor = PdfWriter()
    for ruta in rutas:
        escritor.append(_abrir_pdf(ruta))

    salida = Path(salida)
    with open(salida, "wb") as f:
        escritor.write(f)
    return salida


def separar_pdf(ruta: str | Path, carpeta_salida: str | Path) -> list[Path]:
    """Separa un PDF en un archivo por página: nombre_p1.pdf, nombre_p2.pdf..."""
    lector = _abrir_pdf(ruta)
    total = len(lector.pages)
    return dividir_por_rangos(ruta, f"1-{total}", carpeta_salida, por_pagina=True)


def dividir_por_rangos(
    ruta: str | Path,
    rangos: str,
    carpeta_salida: str | Path,
    por_pagina: bool = False,
) -> list[Path]:
    """
    Crea un PDF por cada rango. Ej: "1-3, 4-6" -> dos archivos.
    Con por_pagina=True, cada página de los rangos va a su propio archivo.
    """
    ruta = Path(ruta)
    lector = _abrir_pdf(ruta)
    grupos = parsear_rangos(rangos, len(lector.pages))
    if por_pagina:
        grupos = [[p] for grupo in grupos for p in grupo]

    carpeta = Path(carpeta_salida)
    carpeta.mkdir(parents=True, exist_ok=True)

    creados: list[Path] = []
    for grupo in grupos:
        escritor = PdfWriter()
        for num in grupo:
            escritor.add_page(lector.pages[num])
        if len(grupo) == 1:
            sufijo = f"p{grupo[0] + 1}"
        else:
            sufijo = f"p{grupo[0] + 1}-{grupo[-1] + 1}"
        destino = carpeta / f"{ruta.stem}_{sufijo}.pdf"
        with open(destino, "wb") as f:
            escritor.write(f)
        creados.append(destino)
    return creados


def extraer_paginas(ruta: str | Path, rangos: str, salida: str | Path) -> Path:
    """Crea UN único PDF con las páginas indicadas. Ej: "1, 3, 5-7"."""
    lector = _abrir_pdf(ruta)
    grupos = parsear_rangos(rangos, len(lector.pages))

    escritor = PdfWriter()
    for grupo in grupos:
        for num in grupo:
            escritor.add_page(lector.pages[num])

    salida = Path(salida)
    with open(salida, "wb") as f:
        escritor.write(f)
    return salida


def _imagen_a_bytes_compatibles(ruta: Path) -> bytes:
    """
    img2pdf mete las imágenes en el PDF sin recomprimirlas (sin perder calidad),
    pero no acepta algunas (PNG con transparencia, WEBP, GIF...).
    En esos casos la convertimos antes con Pillow.
    """
    datos = ruta.read_bytes()
    try:
        img2pdf.convert(datos)  # prueba rápida
        return datos
    except Exception:
        pass

    with Image.open(ruta) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            fondo = Image.new("RGB", img.size, (255, 255, 255))
            fondo.paste(img, mask=img.split()[-1])  # transparencia -> fondo blanco
            img = fondo
        elif img.mode != "RGB":
            img = img.convert("RGB")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()


def imagenes_a_pdf(rutas: Sequence[str | Path], salida: str | Path) -> Path:
    """Convierte una o varias imágenes en un PDF (una imagen por página)."""
    if not rutas:
        raise PdfToolError("No has seleccionado ninguna imagen.")

    imagenes: list[bytes] = []
    for ruta in rutas:
        ruta = _comprobar_existe(ruta)
        if ruta.suffix.lower() not in FORMATOS_IMAGEN:
            raise PdfToolError(f"'{ruta.name}' no es un formato de imagen soportado.")
        try:
            imagenes.append(_imagen_a_bytes_compatibles(ruta))
        except Exception as e:
            raise PdfToolError(f"No se puede abrir la imagen '{ruta.name}': {e}") from e

    salida = Path(salida)
    with open(salida, "wb") as f:
        f.write(img2pdf.convert(imagenes))
    return salida


def pdf_a_imagenes(
    ruta: str | Path,
    carpeta_salida: str | Path,
    formato: str = "png",
    dpi: int = 150,
) -> list[Path]:
    """
    Guarda cada página del PDF como una imagen.
    dpi = calidad: 72 (pantalla), 150 (normal), 300 (impresión).
    """
    ruta = _comprobar_existe(ruta)
    formato = formato.lower().lstrip(".")
    if formato not in {"png", "jpg", "jpeg"}:
        raise PdfToolError("Formato no soportado. Usa png o jpg.")

    carpeta = Path(carpeta_salida)
    carpeta.mkdir(parents=True, exist_ok=True)

    try:
        documento = pdfium.PdfDocument(ruta)
    except Exception as e:
        raise PdfToolError(f"No se puede leer '{ruta.name}' como PDF: {e}") from e

    creados: list[Path] = []
    try:
        escala = dpi / 72  # los PDFs miden en puntos: 72 puntos = 1 pulgada
        for i in range(len(documento)):
            imagen = documento[i].render(scale=escala).to_pil()
            destino = carpeta / f"{ruta.stem}_p{i + 1}.{formato}"
            if formato in ("jpg", "jpeg"):
                imagen.convert("RGB").save(destino, quality=90)
            else:
                imagen.save(destino)
            creados.append(destino)
    finally:
        documento.close()
    return creados


def rotar_paginas(
    ruta: str | Path,
    grados: int,
    salida: str | Path,
    rangos: str | None = None,
) -> Path:
    """Gira las páginas indicadas (o todas) 90, 180 o 270 grados."""
    if grados % 90 != 0:
        raise PdfToolError("Solo se puede rotar en múltiplos de 90 grados.")

    lector = _abrir_pdf(ruta)
    total = len(lector.pages)
    if rangos:
        a_rotar = {p for grupo in parsear_rangos(rangos, total) for p in grupo}
    else:
        a_rotar = set(range(total))

    escritor = PdfWriter()
    for i, pagina in enumerate(lector.pages):
        if i in a_rotar:
            pagina.rotate(grados)
        escritor.add_page(pagina)

    salida = Path(salida)
    with open(salida, "wb") as f:
        escritor.write(f)
    return salida


def es_imagen(ruta: str | Path) -> bool:
    return Path(ruta).suffix.lower() in FORMATOS_IMAGEN


def filtrar_imagenes(rutas: Iterable[str | Path]) -> list[Path]:
    return [Path(r) for r in rutas if es_imagen(r)]
