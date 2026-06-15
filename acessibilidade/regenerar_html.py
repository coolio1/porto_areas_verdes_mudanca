"""Regenera acessibilidade_verde.html rapidamente (~2s) quando parques_porto.geojson é editado.

Fluxo rápido: editar parques -> python regenerar_html.py -> F5 no browser

Não recalcula cálculos de GEE; reutiliza PNGs em cache em layers/.
Se um PNG não existe, avisa e tenta continuar.
"""

import os
import sys

# Importar função de construção do HTML
from acessibilidade_html import build_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")

BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

# Caminhos dos PNGs em cache
verde_pub_path = os.path.join(LAYERS_DIR, "verde_publico.png")
verde_pago_path = os.path.join(LAYERS_DIR, "verde_pago.png")
acc_path = os.path.join(LAYERS_DIR, "acessibilidade_2sfca.png")
lowpop_path = os.path.join(LAYERS_DIR, "baixa_densidade.png")
muni_path = os.path.join(PARENT_LAYERS, "municipios.png")
prox_path = os.path.join(LAYERS_DIR, "proximidade_300m.png")

# Verificar quais PNGs existem
print("Verificando PNGs em cache...")
for label, path in [
    ("Verde publico", verde_pub_path),
    ("Verde pago", verde_pago_path),
    ("Acessibilidade 2SFCA", acc_path),
    ("Baixa densidade", lowpop_path),
    ("Limites municipais", muni_path),
    ("Proximidade 300m", prox_path),
]:
    status = "[OK]" if os.path.exists(path) else "[MISSING]"
    print(f"  {status} {label}")

print("\nRegenerando acessibilidade_verde.html...")

try:
    build_html(
        SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, BOUNDS,
        verde_pub_path, verde_pago_path, acc_path, lowpop_path,
        muni_path, prox_path
    )
    print("\n[OK] HTML regenerado com sucesso.")
    html_path = os.path.join(SCRIPT_DIR, 'acessibilidade_verde.html').replace(os.sep, '/')
    print(f"  Abrir: file:///{html_path}")
except Exception as e:
    print(f"\n[ERRO] Nao foi possivel regenerar HTML: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
