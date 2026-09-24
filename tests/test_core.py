"""
Tests de la lógica principal. Se ejecutan con:  pytest
Cada test crea sus propios archivos de prueba en una carpeta temporal.
"""

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdftool import core
from pdftool.core import PdfToolError


# ---------- Ayudantes para crear archivos de prueba ----------
def crear_pdf(ruta, paginas=3, ancho=200):
    """Crea un PDF de prueba con páginas en blanco. El ancho sirve para identificarlas."""
    escritor = PdfWriter()
    for i in range(paginas):
        escritor.add_blank_page(width=ancho + i, height=300)
    with open(ruta, "wb") as f:
        escritor.write(f)
    return ruta


def anchos(ruta):
    return [round(float(p.mediabox.width)) for p in PdfReader(ruta).pages]


# ---------- parsear_rangos ----------
def test_parsear_rangos_basico():
    assert core.parsear_rangos("1-3, 5", 10) == [[0, 1, 2], [4]]


def test_parsear_rangos_hasta_el_final():
    assert core.parsear_rangos("8-", 10) == [[7, 8, 9]]


@pytest.mark.parametrize("texto", ["0", "11", "5-3", "abc", "", "1-20"])
def test_parsear_rangos_invalidos(texto):
    with pytest.raises(PdfToolError):
        core.parsear_rangos(texto, 10)


# ---------- unir ----------
def test_unir_pdfs(tmp_path):
    a = crear_pdf(tmp_path / "a.pdf", paginas=2, ancho=100)
    b = crear_pdf(tmp_path / "b.pdf", paginas=3, ancho=500)
    salida = core.unir_pdfs([a, b], tmp_path / "unido.pdf")
    assert anchos(salida) == [100, 101, 500, 501, 502]


def test_unir_necesita_dos(tmp_path):
    a = crear_pdf(tmp_path / "a.pdf")
    with pytest.raises(PdfToolError):
        core.unir_pdfs([a], tmp_path / "x.pdf")


# ---------- separar / dividir / extraer ----------
def test_separar_pdf(tmp_path):
    doc = crear_pdf(tmp_path / "doc.pdf", paginas=4)
    creados = core.separar_pdf(doc, tmp_path / "salida")
    assert [c.name for c in creados] == [f"doc_p{i}.pdf" for i in range(1, 5)]
    assert all(core.contar_paginas(c) == 1 for c in creados)


def test_dividir_por_rangos(tmp_path):
    doc = crear_pdf(tmp_path / "doc.pdf", paginas=6)
    creados = core.dividir_por_rangos(doc, "1-2, 3-6", tmp_path / "salida")
    assert [core.contar_paginas(c) for c in creados] == [2, 4]
    assert creados[1].name == "doc_p3-6.pdf"


def test_extraer_paginas(tmp_path):
    doc = crear_pdf(tmp_path / "doc.pdf", paginas=5, ancho=100)
    salida = core.extraer_paginas(doc, "5, 1-2", tmp_path / "extracto.pdf")
    assert anchos(salida) == [104, 100, 101]


# ---------- rotar ----------
def test_rotar_solo_algunas(tmp_path):
    doc = crear_pdf(tmp_path / "doc.pdf", paginas=3)
    salida = core.rotar_paginas(doc, 90, tmp_path / "rotado.pdf", rangos="2")
    assert [p.rotation for p in PdfReader(salida).pages] == [0, 90, 0]


# ---------- imágenes <-> PDF ----------
def test_imagenes_a_pdf_incluye_png_transparente(tmp_path):
    jpg = tmp_path / "foto.jpg"
    Image.new("RGB", (400, 300), "red").save(jpg)
    png = tmp_path / "logo.png"
    Image.new("RGBA", (200, 200), (0, 0, 255, 128)).save(png)  # con transparencia

    salida = core.imagenes_a_pdf([jpg, png], tmp_path / "fotos.pdf")
    assert core.contar_paginas(salida) == 2


def test_imagenes_a_pdf_rechaza_otros_formatos(tmp_path):
    txt = tmp_path / "nota.txt"
    txt.write_text("hola")
    with pytest.raises(PdfToolError):
        core.imagenes_a_pdf([txt], tmp_path / "x.pdf")


def test_pdf_a_imagenes(tmp_path):
    doc = crear_pdf(tmp_path / "doc.pdf", paginas=2, ancho=144)
    creados = core.pdf_a_imagenes(doc, tmp_path / "imgs", formato="jpg", dpi=144)
    assert [c.name for c in creados] == ["doc_p1.jpg", "doc_p2.jpg"]
    with Image.open(creados[0]) as img:
        assert img.size == (288, 600)  # 144 pt a 144 dpi = 2 pulgadas = 288 px


# ---------- errores ----------
def test_archivo_inexistente(tmp_path):
    with pytest.raises(PdfToolError):
        core.contar_paginas(tmp_path / "no_existe.pdf")


def test_archivo_que_no_es_pdf(tmp_path):
    falso = tmp_path / "falso.pdf"
    falso.write_text("esto no es un pdf")
    with pytest.raises(PdfToolError):
        core.contar_paginas(falso)
