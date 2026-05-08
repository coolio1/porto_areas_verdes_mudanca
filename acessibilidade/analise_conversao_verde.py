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
import numpy as np
from PIL import Image
from scipy import ndimage
from shapely.geometry import mapping, shape
from shapely.ops import unary_union
from rasterio.features import shapes as rasterio_shapes
from rasterio.transform import Affine
from conversao_html import build_html

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
    f"  Cobertura actual (<=300m de parque >=0.4ha): {pop_coberta_actual:.0f} hab ({pct_actual:.1f}%)"
)

# ===== Carregar candidatos por prioridade =====
print("\nA carregar candidatos por prioridade...")

# Grid de coordenadas (para rasterizar GeoJSON)
xs = np.linspace(LON_MIN, LON_MAX, calc_w)
ys = np.linspace(LAT_MAX, LAT_MIN, calc_h)
xx, yy = np.meshgrid(xs, ys)
coords_flat = (xx.ravel(), yy.ravel())

# Carregar verde pago (usado pela expansão e candidatos)
verde_pago_path = os.path.join(LAYERS_DIR, "verde_pago.png")
vp_img = np.array(Image.open(verde_pago_path).convert("RGBA"))

# --- 1. Estratégia de expansão (CMP) — flood-fill de verde pago a partir dos centróides ---
expansao_path = os.path.join(SCRIPT_DIR, "expansao_verde.geojson")
parques_path = os.path.join(SCRIPT_DIR, "parques_porto.geojson")

expansao_candidates = []
if os.path.exists(expansao_path):
    import math
    from heapq import heappush, heappop

    with open(expansao_path, "r", encoding="utf-8") as f:
        exp_data = json.load(f)

    # Carregar verde pago como máscara disponível
    verde_pago_mask_exp = vp_img[:, :, 3] > 0
    already_claimed = np.zeros_like(verde_pago_mask_exp)

    # Processar por área planeada decrescente (maiores primeiro, sem sobreposição)
    features_sorted = sorted(
        exp_data["features"],
        key=lambda f: f["properties"]["area_ha_planeada"],
        reverse=True,
    )

    for feat in features_sorted:
        nome = feat["properties"]["nome"]
        area_plan_m2 = feat["properties"]["area_ha_planeada"] * 10000
        lon, lat = feat["geometry"]["coordinates"]

        # Pixel do centróide
        cx = int(round((lon - LON_MIN) / (LON_MAX - LON_MIN) * (calc_w - 1)))
        cy = int(round((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (calc_h - 1)))

        available = verde_pago_mask_exp & ~already_claimed

        # Se centróide não cai em verde pago, encontrar pixel mais próximo
        seed_y, seed_x = cy, cx
        if not (0 <= cy < calc_h and 0 <= cx < calc_w and available[cy, cx]):
            best_dist = float("inf")
            search_r = 80  # ~500m
            for dy in range(-search_r, search_r + 1):
                for dx in range(-search_r, search_r + 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < calc_h and 0 <= nx < calc_w and available[ny, nx]:
                        d = math.sqrt((dx * px_w_m) ** 2 + (dy * px_h_m) ** 2)
                        if d < best_dist:
                            best_dist = d
                            seed_y, seed_x = ny, nx
            if best_dist == float("inf"):
                print(f"  AVISO: {nome} — sem verde pago acessível, a saltar")
                continue

        # BFS por distância ao centróide, apenas por verde pago contíguo
        captured = np.zeros_like(verde_pago_mask_exp)
        visited = np.zeros_like(verde_pago_mask_exp)
        heap = [(0.0, seed_y, seed_x)]
        visited[seed_y, seed_x] = True
        total_area = 0

        while heap and total_area < area_plan_m2:
            dist, py, px = heappop(heap)
            if not available[py, px]:
                continue
            captured[py, px] = True
            total_area += pixel_area_m2

            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    if dy == 0 and dx == 0:
                        continue
                    ny, nx = py + dy, px + dx
                    if 0 <= ny < calc_h and 0 <= nx < calc_w and not visited[ny, nx]:
                        visited[ny, nx] = True
                        if available[ny, nx]:
                            d = math.sqrt(
                                ((nx - cx) * px_w_m) ** 2 + ((ny - cy) * px_h_m) ** 2
                            )
                            heappush(heap, (d, ny, nx))

        already_claimed |= captured
        rows_i, cols_i = np.where(captured)
        if len(rows_i) == 0:
            continue
        expansao_candidates.append(
            {
                "tipo": "expansao",
                "nome": nome,
                "area_m2": total_area,
                "area_ha": total_area / 10000,
                "area_planeada_ha": feat["properties"]["area_ha_planeada"],
                "lat": LAT_MAX - (rows_i.mean() / calc_h) * (LAT_MAX - LAT_MIN),
                "lon": LON_MIN + (cols_i.mean() / calc_w) * (LON_MAX - LON_MIN),
                "mask": captured,
            }
        )
        pct_cap = total_area / area_plan_m2 * 100
        print(
            f"  {nome:<45} {total_area / 10000:>5.1f}/{feat['properties']['area_ha_planeada']:.0f} ha ({pct_cap:.0f}%)"
        )

    print(f"  Expansao (CMP): {len(expansao_candidates)} areas")
else:
    print("  AVISO: expansao_verde.geojson nao encontrado")

# --- 2. Verde pago ou não usufruível (excluindo pixels já capturados pela expansão) ---
verde_pago_mask = vp_img[:, :, 3] > 0

# Excluir pixels já capturados pela expansão
expansao_total_mask = np.zeros_like(verde_pago_mask)
for exp_c in expansao_candidates:
    expansao_total_mask |= exp_c["mask"]
verde_pago_restante = verde_pago_mask & ~expansao_total_mask

# Clustering: dilatar manchas em 50m, re-labeling, depois usar máscara original
CLUSTER_RADIUS_M = 50
cluster_rx = int(round(CLUSTER_RADIUS_M / px_w_m))
cluster_ry = int(round(CLUSTER_RADIUS_M / px_h_m))
ky_c, kx_c = np.ogrid[-cluster_ry : cluster_ry + 1, -cluster_rx : cluster_rx + 1]
kernel_cluster = (
    (kx_c * px_w_m) ** 2 + (ky_c * px_h_m) ** 2 <= CLUSTER_RADIUS_M**2
).astype(bool)
pago_dilated = ndimage.binary_dilation(verde_pago_restante, structure=kernel_cluster)
pago_labels, n_pago = ndimage.label(pago_dilated)
# Aplicar labels à máscara original (sem dilatação)
pago_labels = pago_labels * verde_pago_restante

pago_candidates = []
for rid in range(1, n_pago + 1):
    rmask = pago_labels == rid
    area_m2 = rmask.sum() * pixel_area_m2
    if area_m2 < 1:
        continue
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
n_clustered = n_pago - len(pago_candidates)
print(
    f"  Verde pago restante: {len(pago_candidates)} clusters (agrupados a <{CLUSTER_RADIUS_M}m)"
)

# --- 3. Verde privado (com clustering a 50m) ---
verde_priv_path = os.path.join(PARENT_LAYERS, "interior_subsistente.png")
vr_img = np.array(Image.open(verde_priv_path).convert("RGBA"))
verde_priv_mask = vr_img[:, :, 3] > 0

priv_dilated = ndimage.binary_dilation(verde_priv_mask, structure=kernel_cluster)
priv_labels, n_priv = ndimage.label(priv_dilated)
priv_labels = priv_labels * verde_priv_mask

priv_candidates = []
for rid in range(1, n_priv + 1):
    rmask = priv_labels == rid
    area_m2 = rmask.sum() * pixel_area_m2
    if area_m2 < 1:
        continue
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
print(
    f"  Verde privado: {len(priv_candidates)} clusters (agrupados a <{CLUSTER_RADIUS_M}m)"
)

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


# Categoria 1: Expansão CMP — incondicional (todas as expansões são implementadas)
print("  --- Expansao CMP (incondicional) ---")
for exp_c in expansao_candidates:
    reach_new = ndimage.binary_dilation(exp_c["mask"], structure=kernel_300_bool)
    coberto_novo = coberto | (reach_new & porto_mask)
    pop_nova = pop_corrected[coberto_novo & habitado].sum()
    delta = pop_nova - pop_coberta

    exp_c["rank"] = len(selected) + 1
    exp_c["pop_delta"] = delta
    exp_c["pct_antes"] = pop_coberta / total_pop * 100
    exp_c["pct_depois"] = pop_nova / total_pop * 100
    exp_c["pop_coberta_acum"] = pop_nova
    selected.append(exp_c)

    coberto = coberto_novo
    pop_coberta = pop_nova
    pct = exp_c["pct_depois"]

    print(
        f"  #{exp_c['rank']:>2}: {exp_c['nome']:<35} {exp_c['area_ha']:>6.2f} ha  "
        f"+{delta:>6.0f} hab  -> {pct:.1f}%"
    )
print(f"  Apos expansao CMP: {pct:.1f}%")

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

build_html(SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, geojson, pct_actual, pct, TARGET_PCT, BOUNDS)
