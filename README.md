# PDF Toolkit

Aplicación de escritorio en Python para trabajar con PDFs de forma sencilla y **sin subir tus archivos a internet**.

> Proyecto en desarrollo. La lógica ya funciona y tiene tests; la interfaz gráfica está en camino.

## Funciones

| Operación | Estado |
|---|---|
| Unir varios PDFs en uno 
| Separar un PDF en páginas sueltas 
| Dividir un PDF por rangos (`1-3, 4-10`) 
| Extraer páginas concretas a un nuevo PDF 
| Rotar páginas | 
| Imágenes (JPG, PNG, WEBP...) -> PDF | 
| PDF -> imágenes (PNG / JPG) | 
| Interfaz gráfica de escritorio | WIP |

## Tecnologías

- [pypdf](https://github.com/py-pdf/pypdf): unir, separar y rotar
- [img2pdf](https://gitlab.mister-muffin.de/josch/img2pdf): imágenes -> PDF sin pérdida de calidad
- [pypdfium2](https://github.com/pypdfium2-team/pypdfium2): PDF -> imágenes
- [Pillow](https://python-pillow.org/): tratamiento de imágenes
- [pytest](https://pytest.org/): tests automáticos

## Instalación

```bash
git clone https://github.com/jugabe24/pdf-toolkit.git
cd pdf-toolkit
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Ejecutar los tests

```bash
pytest
```

## Estructura

```
pdf-toolkit/
├── pdftool/
│   └── core.py        # lógica: unir, separar, convertir...
├── tests/
│   └── test_core.py   # tests automáticos
├── requirements.txt
└── README.md
```

La lógica (`core.py`) está separada de la interfaz, así que se puede probar de forma independiente y reutilizar desde otras interfaces.

## Licencia

MIT
