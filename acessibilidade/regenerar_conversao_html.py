"""Regenera conversao_verde.html rapidamente (~2s) sem recalcular métricas/GEE.

Uso:
  python regenerar_conversao_html.py

Este script é útil após editar candidatos_conversao.geojson — regenera o HTML
sem esperar por recálculos pesados.

Para recalcular tudo (métricas + HTML):
  python analise_conversao_verde.py
"""

import os
import numpy as np
import json
from conversao_html import build_html

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

print("Regenerando conversao_verde.html (~2s)...")

# Carregar candidatos do disco (editados manualmente)
candidatos_path = os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson")
if not os.path.exists(candidatos_path):
    print(f"ERRO: {candidatos_path} não encontrado")
    raise SystemExit(1)

with open(candidatos_path, "r", encoding="utf-8") as f:
    geojson = json.load(f)

# Carregar métricas do cache anterior
params_path = os.path.join(LAYERS_DIR, "calc_params.npz")
if not os.path.exists(params_path):
    print(f"ERRO: {params_path} não encontrado — correr analise_conversao_verde.py primeiro")
    raise SystemExit(1)

params = np.load(params_path, allow_pickle=True)
pct_actual = float(params.get("pct_actual", 0))
pct_sim = float(params.get("pct_sim", 0))
sfca_actual_pct = float(params.get("sfca_actual_pct", 0)) if "sfca_actual_pct" in params else None
sfca_sim_pct = float(params.get("sfca_sim_pct", 0)) if "sfca_sim_pct" in params else None

build_html(
    SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, geojson,
    pct_actual, pct_sim, 80.0, BOUNDS,
    sfca_actual_pct=sfca_actual_pct,
    sfca_sim_pct=sfca_sim_pct
)
print("OK — HTML regenerado com candidatos do disco")
