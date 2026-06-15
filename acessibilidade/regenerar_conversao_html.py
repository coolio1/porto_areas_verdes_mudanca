"""Regenera conversao_verde.html rapidamente (~2s) quando candidatos_conversao.geojson é editado.

Fluxo rápido: editar candidatos -> python regenerar_conversao_html.py -> F5 no browser

Não recalcula cálculos de simulação; reutiliza PNGs em cache e dados de cobertura existentes.
Se um PNG não existe, avisa e tenta continuar.
"""

import os
import sys
import json

# Importar função de construção do HTML
from conversao_html import build_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")

BOUNDS = [[41.13, -8.70], [41.19, -8.54]]
TARGET_PCT = 80.0

# Carregar dados de cobertura do ficheiro de metadados
metadata_path = os.path.join(LAYERS_DIR, "conversao_metadata.json")
pct_actual = None
pct = None
sfca_actual_pct = None
sfca_sim_pct = None

if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
            pct_actual = metadata.get("pct_actual", 0)
            pct = metadata.get("pct_simulado", 0)
            sfca_actual_pct = metadata.get("sfca_actual_pct")
            sfca_sim_pct = metadata.get("sfca_sim_pct")
        print(f"[OK] Metadados carregados: {pct_actual:.1f}% -> {pct:.1f}%")
    except Exception as e:
        print(f"[AVISO] Nao foi possivel carregar metadados: {e}")
else:
    print("[AVISO] conversao_metadata.json nao encontrado")
    print("  Nota: dados de cobertura serao vazios ate correr analise_conversao_verde.py")

# Carregar candidatos do GeoJSON
candidatos_path = os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson")
if not os.path.exists(candidatos_path):
    print(f"[ERRO] {candidatos_path} nao encontrado")
    sys.exit(1)

try:
    with open(candidatos_path, "r", encoding="utf-8") as f:
        candidatos_geojson = json.load(f)
    print(f"[OK] Carregados {len(candidatos_geojson.get('features', []))} candidatos")
except json.JSONDecodeError as e:
    print(f"[ERRO] candidatos_conversao.geojson invalido: {e}")
    print(f"  Verificar sintaxe JSON no ficheiro")
    sys.exit(1)

# Verificar quais PNGs existem
print("\nVerificando PNGs em cache...")
for label, path in [
    ("Proximidade actual", os.path.join(LAYERS_DIR, "proximidade_300m.png")),
    ("Proximidade simulada", os.path.join(LAYERS_DIR, "proximidade_simulada.png")),
    ("Acessibilidade 2SFCA actual", os.path.join(LAYERS_DIR, "acessibilidade_2sfca.png")),
    ("Acessibilidade 2SFCA simulada", os.path.join(LAYERS_DIR, "acessibilidade_2sfca_sim.png")),
    ("Baixa densidade", os.path.join(LAYERS_DIR, "baixa_densidade.png")),
]:
    status = "[OK]" if os.path.exists(path) else "[MISSING]"
    print(f"  {status} {label}")

print("\nRegenerando conversao_verde.html...")

try:
    build_html(
        SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, candidatos_geojson,
        pct_actual, pct, TARGET_PCT, BOUNDS,
        sfca_actual_pct, sfca_sim_pct
    )
    print("\n[OK] HTML regenerado com sucesso.")
    html_path = os.path.join(SCRIPT_DIR, 'conversao_verde.html').replace(os.sep, '/')
    print(f"  Abrir: file:///{html_path}")
except Exception as e:
    print(f"\n[ERRO] Nao foi possivel regenerar HTML: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
