"""Regenera acessibilidade_verde.html rapidamente (~2s) sem cálculos GEE/arrays.

Uso:
  python regenerar_html.py

Este script é útil após editar parques_porto.geojson — regenera o HTML
sem esperar por recálculos de 1-2 min em GEE.

Para recalcular tudo (GEE + arrays + HTML):
  python acessibilidade_verde.py
"""

import os
from acessibilidade_html import build_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

print("Regenerando acessibilidade_verde.html (~2s)...")
build_html(
    SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, BOUNDS,
    os.path.join(LAYERS_DIR, "verde_publico.png"),
    os.path.join(LAYERS_DIR, "verde_pago.png"),
    os.path.join(LAYERS_DIR, "acessibilidade_2sfca.png"),
    os.path.join(LAYERS_DIR, "baixa_densidade.png"),
    os.path.join(PARENT_LAYERS, "municipios.png"),
    os.path.join(LAYERS_DIR, "proximidade_300m.png"),
)
print("OK — HTML regenerado com dados do disco")
