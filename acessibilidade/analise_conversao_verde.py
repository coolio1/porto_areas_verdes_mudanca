"""
Análise de conversão de verde para colmatar défice de proximidade (300m).

Calcula a cobertura actual e simulada (com todos os candidatos manuais
implementados) usando o critério Konijnendijk 3-30-300 (≤300m de parque ≥0,4 ha).

Os candidatos são editados manualmente em candidatos_conversao.geojson.
Este script não gera nem propõe novos candidatos — apenas calcula métricas
e regenera conversao_verde.html e layers/proximidade_simulada.png.

Lê:
  - arrays em cache (.npy) do script acessibilidade_verde.py
  - candidatos_conversao.geojson (editado manualmente)

Gera:
  - layers/proximidade_simulada.png
  - conversao_verde.html
"""

import os
import sys
import json
import numpy as np
from PIL import Image
from scipy import ndimage
from shapely.geometry import shape
from rasterio.features import rasterize
from rasterio.transform import Affine
from conversao_html import build_html

CLASSES_COLOR = [
    (0,   3,   np.array([183,  28,  28])),  # vermelho — défice crítico
    (3,   9,   np.array([232, 168,  56])),  # laranja — insuficiente
    (9, 999,   np.array([ 46, 125,  50])),  # verde — adequado
]

# ===== Configuração =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")

LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

PARK_MIN_AREA_M2 = 4_000  # 0.4 ha (critério Konijnendijk)
TARGET_PCT = 80.0

# ===== Carregar arrays em cache =====
print("A carregar arrays em cache...")
required = [
    "pop_corrected.npy",
    "porto_mask.npy",
    "calc_params.npz",
    "kernel_300.npy",
    "reach_300.npy",
    "pop_500m.npy",
]
for fname in required:
    path = os.path.join(LAYERS_DIR, fname)
    if not os.path.exists(path):
        print(f"  ERRO: {fname} nao encontrado. Correr acessibilidade_verde.py primeiro.")
        raise SystemExit(1)

pop_corrected = np.load(os.path.join(LAYERS_DIR, "pop_corrected.npy"))
porto_mask = np.load(os.path.join(LAYERS_DIR, "porto_mask.npy"))
kernel_300 = np.load(os.path.join(LAYERS_DIR, "kernel_300.npy"))
reach_300 = np.load(os.path.join(LAYERS_DIR, "reach_300.npy"))
pop_500m = np.load(os.path.join(LAYERS_DIR, "pop_500m.npy"))

params = np.load(os.path.join(LAYERS_DIR, "calc_params.npz"))
pixel_area_m2 = float(params["pixel_area_m2"])
POP_500M_MIN = float(params["POP_500M_MIN"])
calc_h, calc_w = int(params["calc_h"]), int(params["calc_w"])

print(f"  Arrays carregados: {calc_w}x{calc_h}, pixel={pixel_area_m2:.0f} m2")

# Cobertura actual (baseline)
habitado = porto_mask & (pop_500m >= POP_500M_MIN)
total_pop = pop_corrected[porto_mask].sum()
if total_pop == 0:
    print("ERRO: população total zero — verificar porto_mask e pop_corrected")
    sys.exit(1)
coberto_actual = reach_300 & porto_mask
pop_coberta_actual = pop_corrected[coberto_actual & habitado].sum()
pct_actual = pop_coberta_actual / total_pop * 100
print(f"  Populacao total: {total_pop:.0f} hab")
print(f"  Cobertura actual (<=300m de parque >=0.4ha): {pop_coberta_actual:.0f} hab ({pct_actual:.1f}%)")

# ===== Carregar candidatos manuais =====
geojson_path = os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson")
with open(geojson_path, encoding="utf-8") as f:
    geojson = json.load(f)

print(f"\nCandidatos manuais: {len(geojson['features'])} areas")

# Transformação affine: coordenadas geográficas → pixel
transform = Affine(
    (LON_MAX - LON_MIN) / calc_w, 0, LON_MIN,
    0, -(LAT_MAX - LAT_MIN) / calc_h, LAT_MAX,
)
kernel_300_bool = kernel_300 > 0

# ===== Cobertura simulada (todos os candidatos implementados) =====
print("\nA calcular cobertura simulada...")
coberto_sim = coberto_actual.copy()

for feat in sorted(geojson["features"], key=lambda f: f["properties"]["rank"]):
    props = feat["properties"]
    area_m2 = props["area_ha"] * 10000
    if area_m2 < PARK_MIN_AREA_M2:
        print(f"  #{props['rank']:>2} {props.get('nome', '(sem nome)'):<35} — ignorado (area < 0.4 ha)")
        continue
    geom = shape(feat["geometry"])
    mask = rasterize(
        [(geom, 1)],
        out_shape=(calc_h, calc_w),
        transform=transform,
        fill=0,
        dtype=np.uint8,
    ).astype(bool)
    reach_new = ndimage.binary_dilation(mask, structure=kernel_300_bool)
    coberto_sim |= reach_new & porto_mask

pop_coberta_sim = pop_corrected[coberto_sim & habitado].sum()
pct_sim = pop_coberta_sim / total_pop * 100
print(f"  Cobertura simulada: {pop_coberta_sim:.0f} hab ({pct_sim:.1f}%)")
print(f"  (actual: {pct_actual:.1f}% -> simulado: {pct_sim:.1f}%)")

# ===== Gerar PNG de proximidade simulada =====
print("\nA gerar layers/proximidade_simulada.png...")
prox_sim_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
prox_sim_rgba[habitado & coberto_sim] = [46, 125, 50, 255]    # verde (#2E7D32)
prox_sim_rgba[habitado & ~coberto_sim] = [183, 28, 28, 255]   # vermelho (#B71C1C)
prox_sim_path = os.path.join(LAYERS_DIR, "proximidade_simulada.png")
Image.fromarray(prox_sim_rgba).save(prox_sim_path)
print(f"  Guardado ({os.path.getsize(prox_sim_path) // 1024} KB)")

# ===== 2SFCA simulado =====
print("\nA calcular 2SFCA simulado...")

green_m2    = np.load(os.path.join(LAYERS_DIR, "green_m2.npy"))
kernel_2sfca = np.load(os.path.join(LAYERS_DIR, "kernel_2sfca.npy"))
accessibility = np.load(os.path.join(LAYERS_DIR, "accessibility.npy"))
params2 = np.load(os.path.join(LAYERS_DIR, "calc_params.npz"))
px_w_m = float(params2["px_w_m"])
px_h_m = float(params2["px_h_m"])

# Rasterizar todos os parques existentes
parques_path = os.path.join(SCRIPT_DIR, "parques_porto.geojson")
with open(parques_path, encoding="utf-8") as f:
    parques_geojson = json.load(f)

park_mask = np.zeros((calc_h, calc_w), dtype=bool)
for feat in parques_geojson["features"]:
    geom = shape(feat["geometry"])
    m = rasterize([(geom, 1)], out_shape=(calc_h, calc_w),
                  transform=transform, fill=0, dtype=np.uint8).astype(bool)
    park_mask |= m
print(f"  Parques: {park_mask.sum()} px = {park_mask.sum() * pixel_area_m2 / 10000:.1f} ha")

# Rasterizar todos os candidatos
cand_mask_all = np.zeros((calc_h, calc_w), dtype=bool)
for feat in geojson["features"]:
    geom = shape(feat["geometry"])
    m = rasterize([(geom, 1)], out_shape=(calc_h, calc_w),
                  transform=transform, fill=0, dtype=np.uint8).astype(bool)
    cand_mask_all |= m
print(f"  Candidatos: {cand_mask_all.sum()} px = {cand_mask_all.sum() * pixel_area_m2 / 10000:.1f} ha")

# Verde simulado: parques + candidatos completamente verdes
green_m2_sim = green_m2.copy()
green_m2_sim[park_mask]    = pixel_area_m2
green_m2_sim[cand_mask_all] = pixel_area_m2

green_500m_sim  = ndimage.convolve(green_m2_sim, kernel_2sfca, mode="constant", cval=0.0)
pop_500m_safe = np.where(pop_500m > 0, pop_500m, 1)  # evita divisão por zero em np.where
accessibility_sim = np.where(pop_500m >= POP_500M_MIN, green_500m_sim / pop_500m_safe, np.nan)

# Estatísticas comparativas
valid_act = ~np.isnan(accessibility)  & porto_mask
valid_sim = ~np.isnan(accessibility_sim) & porto_mask
print("\n  2SFCA — actual vs simulado (% pop):")
for lo, hi, color in CLASSES_COLOR:
    label = {0:"Defice critico (<3 m2/hab)", 3:"Insuficiente (3-9)", 9:"Adequado (>=9)"}[lo]
    pa = pop_corrected[valid_act & (accessibility     >= lo) & (accessibility     < hi)].sum() / total_pop * 100
    ps = pop_corrected[valid_sim & (accessibility_sim >= lo) & (accessibility_sim < hi)].sum() / total_pop * 100
    print(f"  {label}: {pa:.1f}% -> {ps:.1f}%")

sfca_actual_pct = pop_corrected[valid_act & (accessibility >= 9)].sum() / total_pop * 100
sfca_sim_pct    = pop_corrected[valid_sim & (accessibility_sim >= 9)].sum() / total_pop * 100

# Gerar acessibilidade_2sfca_sim.png (mesma paleta que acessibilidade_verde.py)
acc_sim_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
for lo, hi, color in CLASSES_COLOR:
    m = valid_sim & (accessibility_sim >= lo) & (accessibility_sim < hi)
    acc_sim_rgba[m, 0:3] = color
    acc_sim_rgba[m, 3] = 255
acc_sim_rgba[~porto_mask, 3] = 0

acc_sim_path = os.path.join(LAYERS_DIR, "acessibilidade_2sfca_sim.png")
Image.fromarray(acc_sim_rgba).save(acc_sim_path)
print(f"  Guardado ({os.path.getsize(acc_sim_path) // 1024} KB)")
print(f"  Pop adequada: {sfca_actual_pct:.1f}% -> {sfca_sim_pct:.1f}%")

# ===== Gerar HTML =====
build_html(SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, geojson,
           pct_actual, pct_sim, TARGET_PCT, BOUNDS,
           sfca_actual_pct=sfca_actual_pct, sfca_sim_pct=sfca_sim_pct)
