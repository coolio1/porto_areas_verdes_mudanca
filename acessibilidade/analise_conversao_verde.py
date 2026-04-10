"""
Análise de conversão de verde para colmatar défice de proximidade (300m).

Simula a adição sequencial de espaços verdes — estratégia de expansão (CMP),
verde pago ou não usufruível, e verde privado — até atingir ~80% da população
a ≤300m de um parque ≥0,4 ha (critério Konijnendijk 3-30-300).

Lê arrays em cache (.npy) do script acessibilidade_verde.py e gera:
  - layers/candidatos_conversao.png (overlay)
  - candidatos_conversao.geojson (polígonos vectorizados)
  - conversao_verde.html (mapa interactivo dedicado)
"""

import os
import json
import base64
import numpy as np
from PIL import Image
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
import geopandas as gpd
from shapely import contains_xy
from rasterio.features import shapes as rasterio_shapes
from rasterio.transform import Affine

# ===== Configuração =====
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")

LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

PARK_MIN_AREA_M2 = 4_000  # 0.4 ha
TARGET_PCT = 80.0  # objectivo: 80% da população coberta

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
for f in required:
    path = os.path.join(LAYERS_DIR, f)
    if not os.path.exists(path):
        print(f"  ERRO: {f} nao encontrado. Correr acessibilidade_verde.py primeiro.")
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
px_w_m = float(params["px_w_m"])
px_h_m = float(params["px_h_m"])

print(f"  Arrays carregados: {calc_w}x{calc_h}, pixel={pixel_area_m2:.0f} m2")

# População total e cobertura actual
habitado = porto_mask & (pop_500m >= POP_500M_MIN)
total_pop = pop_corrected[porto_mask].sum()
coberto_actual = reach_300 & porto_mask
pop_coberta_actual = pop_corrected[coberto_actual & habitado].sum()
pct_actual = pop_coberta_actual / total_pop * 100
print(f"  Populacao total: {total_pop:.0f} hab")
print(
    f"  Cobertura actual (<=300m de parque >=0.5ha): {pop_coberta_actual:.0f} hab ({pct_actual:.1f}%)"
)

# ===== Carregar candidatos por prioridade =====
print("\nA carregar candidatos por prioridade...")

# Grid de coordenadas (para rasterizar GeoJSON)
xs = np.linspace(LON_MIN, LON_MAX, calc_w)
ys = np.linspace(LAT_MAX, LAT_MIN, calc_h)
xx, yy = np.meshgrid(xs, ys)
coords_flat = (xx.ravel(), yy.ravel())

# --- 1. Estratégia de expansão (CMP) ---
expansao_path = os.path.join(SCRIPT_DIR, "expansao_verde.geojson")
parques_path = os.path.join(SCRIPT_DIR, "parques_porto.geojson")

expansao_candidates = []
if os.path.exists(expansao_path):
    exp_gdf = gpd.read_file(expansao_path).to_crs(epsg=4326)
    parques_gdf = gpd.read_file(parques_path).to_crs(epsg=4326)
    parques_union = parques_gdf.geometry.union_all()

    for _, row in exp_gdf.iterrows():
        geom = row.geometry.difference(parques_union)
        if geom.is_empty:
            continue
        inside = contains_xy(geom, *coords_flat).reshape(calc_h, calc_w)
        area_m2 = inside.sum() * pixel_area_m2
        if area_m2 < 1:
            continue
        rows_i, cols_i = np.where(inside)
        cy, cx = rows_i.mean(), cols_i.mean()
        expansao_candidates.append(
            {
                "tipo": "expansao",
                "nome": row.get("nome", ""),
                "area_m2": area_m2,
                "area_ha": area_m2 / 10000,
                "lat": LAT_MAX - (cy / calc_h) * (LAT_MAX - LAT_MIN),
                "lon": LON_MIN + (cx / calc_w) * (LON_MAX - LON_MIN),
                "mask": inside,
            }
        )
    expansao_candidates.sort(key=lambda c: c["area_m2"], reverse=True)
    print(f"  Expansao (CMP): {len(expansao_candidates)} areas")
else:
    print("  AVISO: expansao_verde.geojson nao encontrado")

# --- 2. Verde pago ou não usufruível ---
verde_pago_path = os.path.join(LAYERS_DIR, "verde_pago.png")
vp_img = np.array(Image.open(verde_pago_path).convert("RGBA"))
verde_pago_mask = vp_img[:, :, 3] > 0

pago_labels, n_pago = ndimage.label(verde_pago_mask)
pago_candidates = []
for rid in range(1, n_pago + 1):
    rmask = pago_labels == rid
    area_m2 = rmask.sum() * pixel_area_m2
    rows_i, cols_i = np.where(rmask)
    cy, cx = rows_i.mean(), cols_i.mean()
    pago_candidates.append(
        {
            "tipo": "pago",
            "nome": "",
            "area_m2": area_m2,
            "area_ha": area_m2 / 10000,
            "lat": LAT_MAX - (cy / calc_h) * (LAT_MAX - LAT_MIN),
            "lon": LON_MIN + (cx / calc_w) * (LON_MAX - LON_MIN),
            "mask": rmask,
        }
    )
print(f"  Verde pago ou nao usufruivel: {len(pago_candidates)} regioes")

# --- 2b. Absorção: expansão absorve verde pago próximo (100m) ---
ABSORB_RADIUS_M = 100
absorb_rx = int(round(ABSORB_RADIUS_M / px_w_m))
absorb_ry = int(round(ABSORB_RADIUS_M / px_h_m))
ky_a, kx_a = np.ogrid[-absorb_ry : absorb_ry + 1, -absorb_rx : absorb_rx + 1]
kernel_absorb = (
    (kx_a * px_w_m) ** 2 + (ky_a * px_h_m) ** 2 <= ABSORB_RADIUS_M**2
).astype(bool)

absorbed_indices = set()
for exp_c in expansao_candidates:
    exp_dilated = ndimage.binary_dilation(exp_c["mask"], structure=kernel_absorb)
    for j, pago_c in enumerate(pago_candidates):
        if j in absorbed_indices:
            continue
        if (exp_dilated & pago_c["mask"]).any():
            # Absorver: unir máscara do verde pago à expansão
            exp_c["mask"] = exp_c["mask"] | pago_c["mask"]
            absorbed_indices.add(j)

# Actualizar área das expansões que absorveram verde pago
for exp_c in expansao_candidates:
    exp_c["area_m2"] = exp_c["mask"].sum() * pixel_area_m2
    exp_c["area_ha"] = exp_c["area_m2"] / 10000
    rows_i, cols_i = np.where(exp_c["mask"])
    exp_c["lat"] = LAT_MAX - (rows_i.mean() / calc_h) * (LAT_MAX - LAT_MIN)
    exp_c["lon"] = LON_MIN + (cols_i.mean() / calc_w) * (LON_MAX - LON_MIN)

# Remover regiões pago absorvidas
pago_candidates = [
    c for j, c in enumerate(pago_candidates) if j not in absorbed_indices
]
print(
    f"  Absorcao: {len(absorbed_indices)} regioes pago absorvidas por expansao (buffer {ABSORB_RADIUS_M}m)"
)
print(f"  Verde pago restante: {len(pago_candidates)} regioes")

# --- 3. Verde privado ---
verde_priv_path = os.path.join(PARENT_LAYERS, "interior_subsistente.png")
vr_img = np.array(Image.open(verde_priv_path).convert("RGBA"))
verde_priv_mask = vr_img[:, :, 3] > 0

priv_labels, n_priv = ndimage.label(verde_priv_mask)
priv_candidates = []
for rid in range(1, n_priv + 1):
    rmask = priv_labels == rid
    area_m2 = rmask.sum() * pixel_area_m2
    rows_i, cols_i = np.where(rmask)
    cy, cx = rows_i.mean(), cols_i.mean()
    priv_candidates.append(
        {
            "tipo": "privado",
            "nome": "",
            "area_m2": area_m2,
            "area_ha": area_m2 / 10000,
            "lat": LAT_MAX - (cy / calc_h) * (LAT_MAX - LAT_MIN),
            "lon": LON_MIN + (cx / calc_w) * (LON_MAX - LON_MIN),
            "mask": rmask,
        }
    )
print(f"  Verde privado: {len(priv_candidates)} regioes")

# ===== Simulação greedy por impacto populacional =====
# Dentro de cada categoria (expansão → pago → privado), escolher iterativamente
# o candidato que cobre mais população não coberta (greedy best-first).
print(f"\nA simular adicao greedy (objectivo: {TARGET_PCT:.0f}% cobertura)...")

TIPO_LABELS = {
    "expansao": "Estrategia de expansao (CMP)",
    "pago": "Verde pago ou nao usufruivel",
    "privado": "Verde privado",
}

coberto = coberto_actual.copy()
pop_coberta = pop_coberta_actual
pct = pct_actual
selected = []

kernel_300_bool = kernel_300 > 0
kr, kc = kernel_300.shape[0] // 2, kernel_300.shape[1] // 2


def greedy_select(candidates, coberto, pop_coberta, pct, selected):
    """Selecciona candidatos por impacto populacional decrescente (greedy)."""
    remaining = list(range(len(candidates)))
    while remaining and pct < TARGET_PCT:
        best_idx = None
        best_delta = 0
        best_coberto = None
        best_pop = 0
        best_pct = 0

        for idx in remaining:
            c = candidates[idx]
            if c["area_m2"] < PARK_MIN_AREA_M2:
                continue
            mask_i = c["mask"]
            # Pré-filtro: bbox + margem do kernel intersecta zonas não cobertas?
            rows_i, cols_i = np.where(mask_i)
            r_lo = max(0, rows_i.min() - kr)
            r_hi = min(calc_h, rows_i.max() + kr + 1)
            c_lo = max(0, cols_i.min() - kc)
            c_hi = min(calc_w, cols_i.max() + kc + 1)
            nao_coberto_local = (
                habitado[r_lo:r_hi, c_lo:c_hi] & ~coberto[r_lo:r_hi, c_lo:c_hi]
            )
            if not nao_coberto_local.any():
                continue

            reach_new = ndimage.binary_dilation(mask_i, structure=kernel_300_bool)
            coberto_novo = coberto | (reach_new & porto_mask)
            pop_nova = pop_corrected[coberto_novo & habitado].sum()
            delta = pop_nova - pop_coberta

            if delta > best_delta:
                best_idx = idx
                best_delta = delta
                best_coberto = coberto_novo
                best_pop = pop_nova
                best_pct = pop_nova / total_pop * 100

        if best_idx is None or best_delta < 1:
            break

        c = candidates[best_idx]
        remaining.remove(best_idx)
        pct = best_pct
        c["rank"] = len(selected) + 1
        c["pop_delta"] = best_delta
        c["pct_antes"] = pop_coberta / total_pop * 100
        c["pct_depois"] = best_pct
        c["pop_coberta_acum"] = best_pop
        selected.append(c)

        coberto = best_coberto
        pop_coberta = best_pop

        print(
            f"  #{c['rank']:>2}: {TIPO_LABELS[c['tipo']][:20]:<20} {c['area_ha']:>6.2f} ha  "
            f"+{best_delta:>6.0f} hab  -> {pct:.1f}%"
            f"{'  ' + c['nome'] if c['nome'] else ''}"
        )

    return coberto, pop_coberta, pct


# Categoria 1: Expansão CMP
print("  --- Expansao CMP ---")
coberto, pop_coberta, pct = greedy_select(
    expansao_candidates, coberto, pop_coberta, pct, selected
)

# Categoria 2: Verde pago
if pct < TARGET_PCT:
    print("  --- Verde pago ou nao usufruivel ---")
    coberto, pop_coberta, pct = greedy_select(
        pago_candidates, coberto, pop_coberta, pct, selected
    )

# Categoria 3: Verde privado
if pct < TARGET_PCT:
    print("  --- Verde privado ---")
    coberto, pop_coberta, pct = greedy_select(
        priv_candidates, coberto, pop_coberta, pct, selected
    )

print(f"\n  Resultado: {len(selected)} espacos necessarios para {pct:.1f}% cobertura")
print(f"  (actual: {pct_actual:.1f}% -> {pct:.1f}%)")

# ===== Tabela consola =====
print(f"\n{'=' * 100}")
print("  CANDIDATOS A CONVERSAO — Proximidade 300m (Konijnendijk)")
print(f"{'=' * 100}")
print(
    f"  {'#':>3}  {'Tipo':<30} {'Area(ha)':>8}  {'Pop.delta':>9}  {'Cob.antes':>9}  {'Cob.depois':>10}  {'Nome'}"
)
print(
    f"  {'-' * 3}  {'-' * 30} {'-' * 8}  {'-' * 9}  {'-' * 9}  {'-' * 10}  {'-' * 20}"
)
for c in selected:
    print(
        f"  {c['rank']:>3}  {TIPO_LABELS[c['tipo']]:<30} {c['area_ha']:>8.2f}  "
        f"{c['pop_delta']:>+9.0f}  {c['pct_antes']:>8.1f}%  {c['pct_depois']:>9.1f}%  "
        f"{c.get('nome', '')}"
    )

# ===== Gerar PNG overlay =====
print("\nA gerar layers/candidatos_conversao.png...")
output_arr = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)

COLORS = {
    "expansao": [0, 137, 123],  # #00897B (teal)
    "pago": [141, 110, 99],  # #8D6E63 (castanho)
    "privado": [21, 101, 192],  # #1565C0 (azul)
}

for c in selected:
    color = COLORS[c["tipo"]]
    alpha = max(160, 230 - (c["rank"] - 1) * 3)
    output_arr[c["mask"], :3] = color
    output_arr[c["mask"], 3] = alpha

cand_png_path = os.path.join(LAYERS_DIR, "candidatos_conversao.png")
Image.fromarray(output_arr).save(cand_png_path)
print(f"  Guardado ({os.path.getsize(cand_png_path) // 1024} KB)")

# ===== Gerar PNG de proximidade simulada (com todos os candidatos implementados) =====
print("A gerar layers/proximidade_simulada.png...")
# coberto já tem a cobertura acumulada após todos os candidatos seleccionados
prox_sim_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
prox_sim_rgba[habitado & coberto] = [46, 125, 50, 255]  # verde (#2E7D32)
prox_sim_rgba[habitado & ~coberto] = [183, 28, 28, 255]  # vermelho (#B71C1C)
prox_sim_path = os.path.join(LAYERS_DIR, "proximidade_simulada.png")
Image.fromarray(prox_sim_rgba).save(prox_sim_path)
print(f"  Guardado ({os.path.getsize(prox_sim_path) // 1024} KB)")
print(f"  Cobertura simulada: {pct:.1f}% (vs actual {pct_actual:.1f}%)")

# ===== Gerar GeoJSON (vectorização fiel via rasterio) =====
print("A gerar candidatos_conversao.geojson...")

# Transformação affine: pixel → coordenadas geográficas
transform = Affine(
    (LON_MAX - LON_MIN) / calc_w,
    0,
    LON_MIN,
    0,
    -(LAT_MAX - LAT_MIN) / calc_h,
    LAT_MAX,
)

features = []
for c in selected:
    mask_u8 = c["mask"].astype(np.uint8)
    polys = []
    for geom_dict, val in rasterio_shapes(mask_u8, transform=transform):
        if val == 1:
            polys.append(shape(geom_dict))
    if not polys:
        continue

    poly = unary_union(polys).simplify(0.0002, preserve_topology=True)
    if poly.is_empty:
        continue
    features.append(
        {
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "rank": c["rank"],
                "tipo": TIPO_LABELS[c["tipo"]],
                "nome": c.get("nome", ""),
                "area_ha": round(float(c["area_ha"]), 2),
                "pop_delta": int(float(c["pop_delta"])),
                "pct_antes": round(float(c["pct_antes"]), 1),
                "pct_depois": round(float(c["pct_depois"]), 1),
                "lat": round(float(c["lat"]), 4),
                "lon": round(float(c["lon"]), 4),
            },
        }
    )

geojson = {"type": "FeatureCollection", "features": features}
geojson_path = os.path.join(SCRIPT_DIR, "candidatos_conversao.geojson")
with open(geojson_path, "w", encoding="utf-8") as f:
    json.dump(geojson, f, ensure_ascii=False, indent=2)
print(f"  {len(features)} poligonos guardados")

# ===== Gerar HTML =====
print("\nA construir mapa HTML...")


def to_base64(filepath):
    with open(filepath, "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


cand_b64 = to_base64(cand_png_path)
prox_sim_b64 = to_base64(prox_sim_path)
prox_actual_b64 = to_base64(os.path.join(LAYERS_DIR, "proximidade_300m.png"))
verde_pub_b64 = to_base64(os.path.join(LAYERS_DIR, "verde_publico.png"))
lowpop_b64 = to_base64(os.path.join(LAYERS_DIR, "baixa_densidade.png"))
muni_b64 = to_base64(os.path.join(PARENT_LAYERS, "municipios.png"))

geojson_str = json.dumps(geojson, ensure_ascii=False)

# parques_porto.geojson é carregado via fetch() no HTML

basemaps = [
    (
        "CartoDB Positron",
        "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    ),
    ("CartoDB Dark", "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
    (
        "OpenStreetMap",
        "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    ),
    (
        "Sat\u00e9lite",
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    ),
]
basemap_options = "".join(
    f'<option value="{url}"{"selected" if i == 0 else ""}>{name}</option>'
    for i, (name, url) in enumerate(basemaps)
)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Candidatos a Convers&atilde;o de Verde &mdash; Porto</title>
<meta name="description" content="Simula&ccedil;&atilde;o sequencial de espa&ccedil;os verdes que podem colmatar o d&eacute;fice de proximidade (300m) no Porto.">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #nav {{
    position:fixed; top:10px; right:10px; z-index:1000;
    display:flex; gap:6px; font:11px 'Segoe UI',Arial,sans-serif;
  }}
  #nav a {{
    background:rgba(255,255,255,0.9); color:#444; text-decoration:none;
    padding:4px 10px; border-radius:5px; box-shadow:0 1px 4px rgba(0,0,0,0.15);
  }}
  #nav a:hover {{ background:#fff; color:#222; }}
  #nav a.active {{ background:#00897B; color:#fff; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:280px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }}
  #panel-toggle {{
    display:none; width:100%; border:none; padding:6px 0;
    background:transparent; color:#555; font-size:11px; cursor:pointer;
    text-align:right;
  }}
  .panel-body {{ display:block; }}
  .row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; margin:0; }}
  .row label {{ cursor:pointer; font-size:12px; }}
  .swatch {{ width:14px; height:14px; border-radius:3px; display:inline-block; }}
  .section {{ font-size:11px; color:#888; font-weight:bold; margin:8px 0 4px 0; }}
  select {{ background:#f5f5f5; color:#222; border:1px solid #ccc; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }}
  .park-label {{ background:rgba(255,255,255,0.85)!important; border:none!important; box-shadow:0 1px 3px rgba(0,0,0,0.2); font:10px 'Segoe UI',Arial,sans-serif; color:#1B5E20; padding:1px 5px; border-radius:3px; }}
  .cand-label {{ background:rgba(255,255,255,0.9)!important; border:none!important; box-shadow:0 1px 3px rgba(0,0,0,0.2); font:10px 'Segoe UI',Arial,sans-serif; color:#00695C; padding:1px 5px; border-radius:3px; font-weight:bold; }}
  @media (max-width: 768px) {{
    #panel {{
      left:6px; right:6px; bottom:6px; min-width:unset;
      padding:8px 10px; font-size:11px; line-height:1.3;
      max-height:35vh; overflow-y:auto;
    }}
    #panel b {{ font-size:12px !important; }}
    #panel .section {{ font-size:9px; margin:4px 0 2px; }}
    #panel .row {{ gap:4px; margin:1px 0; }}
    #panel .row input[type=checkbox] {{ width:12px; height:12px; }}
    #panel .row label {{ font-size:10px; }}
    #panel select {{ font-size:10px; padding:2px 4px; }}
    #panel hr {{ margin:4px 0 !important; }}
    #panel .swatch {{ width:10px; height:10px; }}
    #panel.collapsed .panel-body {{ display:none; }}
    #panel-toggle {{ display:block; }}
    #nav {{
      top:4px; right:4px; left:4px;
      flex-wrap:wrap; gap:3px; justify-content:center;
    }}
    #nav a {{ font-size:9px; padding:2px 6px; }}
    .leaflet-top {{ top:50px; }}
    #credit {{ display:none; }}
  }}
</style>
</head>
<body>
<div id="nav">
  <a href="../index.html">In&iacute;cio</a>
  <a href="../mapa.html">Mapa 2016-2025</a>
  <a href="../ndvi_historico.html">Hist&oacute;rico 1947-2024</a>
  <a href="../interiores_quarteiroes.html">Verde Privado</a>
  <a href="acessibilidade_verde.html">Acessibilidade</a>
  <a href="conversao_verde.html" class="active">Convers&atilde;o</a>
  <a href="../atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <button id="panel-toggle" onclick="var p=document.getElementById('panel');p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'&#9650; Abrir legenda':'&#9660; Fechar';">&#9660; Fechar</button>
  <div class="panel-body">
  <b style="font-size:14px;">Candidatos a Convers&atilde;o</b>
  <div style="color:#666;font-size:10px;margin:2px 0 6px;">Simula&ccedil;&atilde;o sequencial para atingir {TARGET_PCT:.0f}% de cobertura a &le;300m (Konijnendijk)</div>

  <div style="margin:4px 0 8px 0;">
    <div class="section">Candidatos (por prioridade)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#00897B;display:inline-block;"></span>
        <span style="color:#666;">Estrat&eacute;gia de expans&atilde;o (CMP)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#8D6E63;display:inline-block;"></span>
        <span style="color:#666;">Verde pago ou n&atilde;o usufru&iacute;vel</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#1565C0;display:inline-block;"></span>
        <span style="color:#666;">Verde privado</span>
      </div>
    </div>
    <div class="section" style="margin-top:6px;">Proximidade 300m (Konijnendijk)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">&le;300m de parque &ge;0,5 ha (cumpre)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">&gt;300m de parque &ge;0,5 ha (n&atilde;o cumpre)</span>
      </div>
    </div>
    <div style="color:#aaa;font-size:9px;margin-top:4px;">Cobertura actual: {pct_actual:.1f}% &rarr; objectivo: {TARGET_PCT:.0f}%</div>
  </div>

  <div class="section">Camadas</div>
  <div id="layer-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Contexto</div>
  <div id="ctx-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#ddd;margin:10px 0 4px 0;">
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; GHS-POP 100m (JRC)<br>
  Crit&eacute;rio: Konijnendijk 3-30-300 (&ge;0,5 ha a &le;300m)</span>
  </div>
</div>

<script>
var candidatosData = {geojson_str};
var parquesData = null;
var map = L.map('map').setView([41.155, -8.63], 13);

fetch('parques_porto.geojson').then(r => r.json()).then(function(data) {{
  parquesData = data;
  if (typeof initParques === 'function') initParques();
}});
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {BOUNDS};

function hexToRgb(h) {{
  h = h.replace('#','');
  return [parseInt(h.substr(0,2),16), parseInt(h.substr(2,2),16), parseInt(h.substr(4,2),16)];
}}

function extractMask(src) {{
  return new Promise(function(r) {{
    var i = new Image();
    i.onload = function() {{
      var c = document.createElement('canvas');
      c.width = i.width; c.height = i.height;
      var x = c.getContext('2d');
      x.drawImage(i, 0, 0);
      var d = x.getImageData(0, 0, c.width, c.height);
      var a = new Uint8Array(d.data.length / 4);
      for (var j = 0; j < a.length; j++) a[j] = d.data[j * 4 + 3];
      r({{w: c.width, h: c.height, alpha: a}});
    }};
    i.src = src;
  }});
}}

function renderColored(m, hex) {{
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = m.w; c.height = m.h;
  var x = c.getContext('2d');
  var d = x.createImageData(m.w, m.h);
  for (var i = 0; i < m.alpha.length; i++) {{
    d.data[i*4] = rgb[0]; d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2]; d.data[i*4+3] = m.alpha[i];
  }}
  x.putImageData(d, 0, 0);
  return c.toDataURL();
}}

async function init() {{
  map.createPane('proxPane');
  map.getPane('proxPane').style.zIndex = 350;
  map.createPane('lowPopPane');
  map.getPane('lowPopPane').style.zIndex = 375;
  map.createPane('candPane');
  map.getPane('candPane').style.zIndex = 450;
  map.createPane('parquesPane');
  map.getPane('parquesPane').style.zIndex = 500;
  map.createPane('candGeoPane');
  map.getPane('candGeoPane').style.zIndex = 550;

  var div = document.getElementById('layer-rows');
  var ctxDiv = document.getElementById('ctx-rows');

  // --- Candidatos raster ---
  var candOverlay = L.imageOverlay("{cand_b64}", bounds, {{opacity: 0.85, pane: 'candPane'}});
  candOverlay.addTo(map);

  // --- Candidatos GeoJSON (contornos + popups) ---
  var candGeoLayer = null;
  if (candidatosData && candidatosData.features.length > 0) {{
    var tipoColors = {{
      'Estrategia de expansao (CMP)': '#00897B',
      'Verde pago ou nao usufruivel': '#8D6E63',
      'Verde privado': '#1565C0'
    }};
    candGeoLayer = L.geoJson(candidatosData, {{
      pane: 'candGeoPane',
      style: function(f) {{
        var color = tipoColors[f.properties.tipo] || '#888';
        return {{
          color: color, weight: 2.5, opacity: 0.9,
          fillColor: color, fillOpacity: 0.05
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var html = '<b style="font-size:13px;">#' + p.rank + '</b>';
        if (p.nome) html += ' &mdash; ' + p.nome;
        html += '<br><span style="color:#666;">' + p.tipo + '</span>';
        html += '<br><span style="color:#666;">&Aacute;rea: ' + p.area_ha + ' ha</span>';
        html += '<br><span style="color:#2E7D32;">+' + p.pop_delta.toLocaleString() + ' hab cobertos</span>';
        html += '<br><span style="color:#444;">Cobertura: ' + p.pct_antes + '% &rarr; ' + p.pct_depois + '%</span>';
        layer.bindPopup(html);
        var label = p.nome ? p.nome : '#' + p.rank;
        layer.bindTooltip(label, {{
          permanent: true, direction: 'center',
          className: 'cand-label',
          offset: [0, 0]
        }});
      }}
    }});
    candGeoLayer.addTo(map);

    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.cand-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 13 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }}

  // Checkbox candidatos
  var cRow = document.createElement('div'); cRow.className = 'row';
  var cCb = document.createElement('input'); cCb.type = 'checkbox'; cCb.checked = true;
  cCb.addEventListener('change', function() {{
    if (this.checked) {{
      candOverlay.addTo(map);
      if (candGeoLayer) candGeoLayer.addTo(map);
    }} else {{
      map.removeLayer(candOverlay);
      if (candGeoLayer) map.removeLayer(candGeoLayer);
    }}
  }});
  var cSw = document.createElement('span'); cSw.className = 'swatch';
  cSw.style.background = 'linear-gradient(135deg, #00897B 33%, #8D6E63 66%, #1565C0 100%)';
  var cLb = document.createElement('label'); cLb.textContent = 'Candidatos a convers\\u00e3o'; cLb.style.fontSize = '12px';
  cRow.appendChild(cCb); cRow.appendChild(cSw); cRow.appendChild(cLb);
  div.appendChild(cRow);

  // --- Proximidade simulada (com candidatos implementados) ---
  var proxSimOverlay = L.imageOverlay("{prox_sim_b64}", bounds, {{opacity: 0.7, pane: 'proxPane'}});
  proxSimOverlay.addTo(map);

  var lowPopOverlay = L.imageOverlay("{lowpop_b64}", bounds, {{pane: 'lowPopPane'}});
  lowPopOverlay.addTo(map);

  // Proximidade actual (para comparação)
  var proxActualOverlay = L.imageOverlay("{prox_actual_b64}", bounds, {{opacity: 0.7, pane: 'proxPane'}});

  var proxSimRow = document.createElement('div'); proxSimRow.className = 'row';
  var proxSimCb = document.createElement('input'); proxSimCb.type = 'checkbox'; proxSimCb.checked = true;
  proxSimCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxSimOverlay.addTo(map); lowPopOverlay.addTo(map);
    }} else {{
      map.removeLayer(proxSimOverlay); map.removeLayer(lowPopOverlay);
    }}
  }});
  var proxSimSw = document.createElement('span'); proxSimSw.className = 'swatch';
  proxSimSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  var proxSimLb = document.createElement('label'); proxSimLb.textContent = 'Proximidade simulada ({pct:.0f}%)'; proxSimLb.style.fontSize = '12px';
  proxSimRow.appendChild(proxSimCb); proxSimRow.appendChild(proxSimSw); proxSimRow.appendChild(proxSimLb);
  div.appendChild(proxSimRow);

  var proxActRow = document.createElement('div'); proxActRow.className = 'row';
  var proxActCb = document.createElement('input'); proxActCb.type = 'checkbox'; proxActCb.checked = false;
  proxActCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxActualOverlay.addTo(map);
      proxSimCb.checked = false; map.removeLayer(proxSimOverlay);
    }} else {{
      map.removeLayer(proxActualOverlay);
    }}
  }});
  proxSimCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxActCb.checked = false; map.removeLayer(proxActualOverlay);
    }}
  }});
  var proxActSw = document.createElement('span'); proxActSw.className = 'swatch';
  proxActSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  proxActSw.style.opacity = '0.5';
  var proxActLb = document.createElement('label'); proxActLb.textContent = 'Proximidade actual ({pct_actual:.0f}%)'; proxActLb.style.fontSize = '12px';
  proxActRow.appendChild(proxActCb); proxActRow.appendChild(proxActSw); proxActRow.appendChild(proxActLb);
  div.appendChild(proxActRow);

  // --- Contexto: parques, municipios ---
  var ctxLayers = [
    {{ id: "verde_publico", label: "Parques e Jardins", color: "#2E7D32", src: "{verde_pub_b64}", show: false }},
    {{ id: "municipios", label: "Limites municipais", color: "#444444", src: "{muni_b64}", show: true }},
  ];
  var ctxOverlays = [];

  for (var i = 0; i < ctxLayers.length; i++) {{
    var L_ = ctxLayers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    ctxOverlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) ctxOverlays[idx].addTo(map); else map.removeLayer(ctxOverlays[idx]);
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    ctxDiv.appendChild(row);
  }}

  // --- Parques GeoJSON (contornos, contexto) — carregado via fetch ---
  window.initParques = function() {{
    if (!parquesData) return;
    var parquesGeoLayer = L.geoJson(parquesData, {{
      pane: 'parquesPane',
      style: function() {{
        return {{
          color: '#1B5E20', weight: 1.5, opacity: 0.6,
          fillColor: '#2E7D32', fillOpacity: 0.03,
          dashArray: '3 3'
        }};
      }},
      onEachFeature: function(f, layer) {{
        layer.bindTooltip(f.properties.nome, {{
          permanent: true, direction: 'center',
          className: 'park-label',
          offset: [0, 0]
        }});
      }}
    }});
    parquesGeoLayer.addTo(map);

    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.park-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 15 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }};

  // Se o fetch() já terminou antes de init(), chamar agora
  if (parquesData) initParques();
}}

init();
</script>
<div id="credit" style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
<script>if(window.innerWidth<=768){{var p=document.getElementById('panel'),b=document.getElementById('panel-toggle');p.classList.add('collapsed');b.textContent='\\u25B2 Abrir legenda';}}</script>
</body>
</html>'''

output_path = os.path.join(SCRIPT_DIR, "conversao_verde.html")
with open(output_path, "w", encoding="utf-8") as fh:
    fh.write(html)

print(f"\nMapa gerado: {output_path}")
print(f"  Tamanho: {os.path.getsize(output_path) // 1024} KB")
print("\nConcluido.")
