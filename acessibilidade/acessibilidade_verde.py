"""
Acessibilidade a áreas verdes públicas no Porto — 2SFCA (500m)

Método Two-Step Floating Catchment Area:
1. Para cada pixel: soma verde público num raio de 500m (m²)
2. Para cada pixel: soma população num raio de 500m (hab)
3. Acessibilidade = verde_500m / pop_500m (m²/hab)

Camadas:
- Verde público (Sentinel-2 2024-25 + 30 parques oficiais) — verde
- Verde pago/não usufruível (PDM fora dos parques) — castanho
- Densidade populacional (GHS-POP 2020) — reutiliza ../layers/ghspop.png
- Acessibilidade 2SFCA — paleta divergente, 70% opacidade, no topo
"""

import ee
import os
import sys
import math
import time
import argparse
import hashlib
import json
import numpy as np
from PIL import Image
from scipy import ndimage
from dotenv import load_dotenv
from acessibilidade_gee import getS2col, getComposite, classify, download_mono_layer, download_greyscale
from acessibilidade_html import build_html

# ===== Modo rápido (--html-only) =====
_parser = argparse.ArgumentParser(description="Acessibilidade a verde público — Porto")
_parser.add_argument('--html-only', action='store_true',
                     help='Regenerar HTML apenas (~2s); sem recalcular GEE/arrays')
_args = _parser.parse_args()

if _args.html_only:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _layers_dir = os.path.join(_script_dir, "layers")
    _parent_layers = os.path.join(os.path.dirname(_script_dir), "layers")
    _bounds = [[41.13, -8.70], [41.19, -8.54]]
    print("Modo rápido: a regenerar HTML sem recalcular...")
    build_html(
        _script_dir, _layers_dir, _parent_layers, _bounds,
        os.path.join(_layers_dir, "verde_publico.png"),
        os.path.join(_layers_dir, "verde_pago.png"),
        os.path.join(_layers_dir, "acessibilidade_2sfca.png"),
        os.path.join(_layers_dir, "baixa_densidade.png"),
        os.path.join(_parent_layers, "municipios.png"),
        os.path.join(_layers_dir, "proximidade_300m.png"),
    )
    print("HTML regenerado. Para recalcular: python acessibilidade_verde.py")
    sys.exit(0)

# ===== Configuração =====
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Geometria do Porto (bbox)
porto = ee.Geometry.Polygon(
    [[[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]]
)
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]
DIM = 2048  # resolução display

# Constantes geográficas
LON_MIN, LON_MAX = -8.70, -8.54
LAT_MIN, LAT_MAX = 41.13, 41.19
LAT_MID = (LAT_MIN + LAT_MAX) / 2
M_PER_DEG_LAT = 111320
M_PER_DEG_LON = 111320 * math.cos(math.radians(LAT_MID))

# Resolução de cálculo (mesma que display para não perder parques pequenos)
CALC_DIM = DIM
RADIUS_M = 500  # raio 2SFCA em metros

# Directórios
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAYERS_DIR = os.path.join(SCRIPT_DIR, "layers")
PARENT_LAYERS = os.path.join(os.path.dirname(SCRIPT_DIR), "layers")
os.makedirs(LAYERS_DIR, exist_ok=True)

municipios = ee.FeatureCollection(f"projects/{GEE_PROJECT}/assets/CAOP2025_municipios")
municipiosPorto = municipios.filterBounds(porto)

esa = ee.Image("ESA/WorldCover/v200/2021").select("Map").clip(porto)
esaBuilt = esa.eq(50)


print("A calcular composito Sentinel-2 (2024-25)...")
s2_late = getComposite([2024, 2025], porto)
ndvi_l = s2_late.select("ndvi")
ndbi_l = s2_late.select("ndbi")
nirgreen_l = s2_late.select("nir_green")
green_l = s2_late.select("green")
spring_ndvi_l = s2_late.select("spring_ndvi")
ndvi_min_l = s2_late.select("ndvi_min")

isTree_l, isBuilt_l, isSolo_l = classify(
    ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l, esaBuilt
)
isGreen_l = isTree_l.Or(isSolo_l)  # árvores + solo/relva

# GHS-POP 2020 (densidade pop 100m)
ghspop = ee.Image("JRC/GHSL/P2023A/GHS_POP/2020").select("population_count").clip(porto)

print("Classificação concluída.")



# ===== Phase 1: Download verde total (display) =====
print("\nA descarregar verde total (display)...")
verde_total_path = os.path.join(LAYERS_DIR, "verde_total.png")
download_mono_layer(isGreen_l.selfMask(), "2E7D32", "verde_total.png", porto, DIM, LAYERS_DIR)

# ===== Phase 2: Máscara PDM — manter só verde PÚBLICO =====
print("\nA aplicar máscara PDM (manter verde público)...")
import geopandas as gpd
from shapely.geometry import MultiPolygon
from shapely import contains_xy

PDM_URL = "https://opendata.porto.digital/dataset/e6bff4b8-ebe8-4048-a3ca-6a1640da8293/resource/44b228a4-1df1-4e67-b44b-c19cfa7bdf97/download/po_cqs.gpkg"
PDM_LOCAL = os.path.join(os.path.dirname(SCRIPT_DIR), "CLC", "po_cqs.gpkg")

if not os.path.exists(PDM_LOCAL):
    print("  A descarregar GeoPackage do PDM (~133 MB)...")
    os.makedirs(os.path.dirname(PDM_LOCAL), exist_ok=True)
    import urllib.request

    for attempt in range(5):
        try:
            urllib.request.urlretrieve(
                PDM_URL,
                PDM_LOCAL,
                reporthook=lambda b, bs, ts: (
                    print(
                        f"\r    {b * bs / 1e6:.0f}/{ts / 1e6:.0f} MB",
                        end="",
                        flush=True,
                    )
                    if b % 200 == 0
                    else None
                ),
            )
            print()
            print(f"  PDM guardado ({os.path.getsize(PDM_LOCAL) // 1024} KB)")
            break
        except Exception as e:
            print(f"\n  Tentativa {attempt + 1} falhou: {e}")
            if os.path.exists(PDM_LOCAL):
                os.remove(PDM_LOCAL)
            if attempt < 4:
                time.sleep(10)
            else:
                raise

# ===== PDM: polígonos de verde (para camada "pago/não usufruível") =====
gdf = gpd.read_file(PDM_LOCAL, layer="PO_QSFUNCIONAL_PL").to_crs(epsg=4326)
VERDE_PDM = [
    "Área verde de fruição coletiva",
    "Área verde lúdico-produtiva",
    "Área verde de proteção e enquadramento",
    "Área verde associada a equipamento",
]
mask_pdm = gdf["sc_espaco"].isin(VERDE_PDM)
if mask_pdm.sum() == 0:
    for val in gdf["sc_espaco"].dropna().unique():
        if "verde" in val.lower() or "frente" in val.lower():
            mask_pdm = mask_pdm | (gdf["sc_espaco"] == val)
pdm_verde = gdf[mask_pdm]
pdm_verde_union = (
    pdm_verde.geometry.union_all() if len(pdm_verde) > 0 else MultiPolygon()
)
print(f"  {len(pdm_verde)} polígonos PDM de verde")

# ===== parques oficiais CMP (fonte autoritativa de verde público) =====
parques_path = os.path.join(SCRIPT_DIR, "parques_porto.geojson")
if not os.path.exists(parques_path):
    raise FileNotFoundError(f"Correr criar_parques.py primeiro: {parques_path}")
parques_gdf = gpd.read_file(parques_path).to_crs(epsg=4326)
parques_union = parques_gdf.geometry.union_all()
print(f"  {len(parques_gdf)} parques oficiais CMP carregados")

# Hash-based cache invalidation: se parques_porto.geojson mudou, regenerar camadas dependentes
CACHE_STATE_PATH = os.path.join(LAYERS_DIR, '.cache_state.json')
_cache_state = {}
if os.path.exists(CACHE_STATE_PATH):
    with open(CACHE_STATE_PATH) as _f:
        try:
            _cache_state = json.load(_f)
        except Exception:
            pass
with open(parques_path, 'rb') as _f:
    _parques_hash = hashlib.sha256(_f.read()).hexdigest()[:16]
parques_changed = _cache_state.get('parques_hash') != _parques_hash
if parques_changed:
    print("  parques_porto.geojson alterado — a invalidar cache verde_pub/verde_pago/prox...")

# Grid de coordenadas (reutilizado por ambas as camadas)
img_ref = Image.open(verde_total_path).convert("RGBA")
grid_w, grid_h = img_ref.size
xs = np.linspace(LON_MIN, LON_MAX, grid_w)
ys = np.linspace(LAT_MAX, LAT_MIN, grid_h)
xx, yy = np.meshgrid(xs, ys)
coords_flat = (xx.ravel(), yy.ravel())

# --- Verde público: Sentinel-2 verde x parques oficiais ---
# Pixels dentro dos parques sem verde Sentinel-2 são pintados com verde sólido
# (jardins pequenos/urbanos onde a copa não domina o pixel)
verde_pub_path = os.path.join(LAYERS_DIR, "verde_publico.png")
if not os.path.exists(verde_pub_path) or parques_changed:
    print("  A mascarar verde para parques oficiais...")
    arr = np.array(img_ref)
    inside_parques = contains_xy(parques_union, *coords_flat).reshape(grid_h, grid_w)
    # Pixels dentro dos parques sem verde Sentinel-2: pintar verde sólido
    sem_verde = inside_parques & (arr[:, :, 3] == 0)
    arr[sem_verde] = [56, 142, 60, 255]  # verde sólido (#388E3C)
    arr[~inside_parques, 3] = 0
    Image.fromarray(arr).save(verde_pub_path)
    n_pub = (arr[:, :, 3] > 0).sum()
    print(f"  verde_publico.png guardado ({n_pub} pixels verdes em parques)")
else:
    print("  verde_publico.png já existe, a saltar...")

# A máscara para o 2SFCA usa os parques
publico_union = parques_union

# --- Verde pago ou não usufruível: (PDM verde x Sentinel-2 verde) \ parques ---
verde_pago_path = os.path.join(LAYERS_DIR, "verde_pago.png")
if not os.path.exists(verde_pago_path) or parques_changed:
    print("  A calcular verde pago (PDM verde x Sentinel-2 verde, fora dos parques)...")
    pdm_minus_parques = pdm_verde_union.difference(parques_union)
    inside_pdm = contains_xy(pdm_minus_parques, *coords_flat).reshape(grid_h, grid_w)
    # Cruzar com pixels verdes reais (Sentinel-2) para excluir edificado
    verde_total_arr = np.array(Image.open(verde_total_path).convert("RGBA"))
    sentinel_green = verde_total_arr[:, :, 3] > 0
    inside_pago = inside_pdm & sentinel_green
    pago_arr = np.zeros((grid_h, grid_w, 4), dtype=np.uint8)
    pago_arr[inside_pago, 3] = 255
    Image.fromarray(pago_arr).save(verde_pago_path)
    n_pago = inside_pago.sum()
    n_removed = inside_pdm.sum() - n_pago
    print(
        f"  verde_pago.png guardado ({n_pago} pixels, {n_removed} edificado removido)"
    )
else:
    print("  verde_pago.png já existe, a saltar...")

# ===== Phase 3: 2SFCA (cálculo a ~30m) =====
print("\nA calcular 2SFCA (300m)...")

# Obter valor máximo de população para normalização
print("  A consultar GHS-POP max...")
pop_max_info = ghspop.reduceRegion(ee.Reducer.max(), porto, 100).getInfo()
POP_MAX = pop_max_info["population_count"]
print(f"  GHS-POP max: {POP_MAX:.1f} hab/pixel")

# Download arrays de cálculo
pop_arr = download_greyscale(ghspop, CALC_DIM, 0, POP_MAX, "GHS-POP calc", porto)

# Verde público: área total dos polígonos dos parques (não Sentinel-2)
print("  A preparar verde público para cálculo...")
vp_img = Image.open(verde_pub_path).convert("RGBA")
display_w, display_h = vp_img.size
# Máscara binária: todos os pixels dentro dos parques contam como verde
inside_parques_calc = contains_xy(parques_union, *coords_flat).reshape(grid_h, grid_w)
green_frac = inside_parques_calc.astype(np.float64)

# Upscalar população para a mesma resolução
pop_upscaled = np.array(
    Image.fromarray(pop_arr.astype(np.float32), mode="F").resize(
        (display_w, display_h), Image.BILINEAR
    )
)

# Dimensões em metros
calc_h, calc_w = display_h, display_w
px_w_m = (LON_MAX - LON_MIN) * M_PER_DEG_LON / calc_w
px_h_m = (LAT_MAX - LAT_MIN) * M_PER_DEG_LAT / calc_h
pixel_area_m2 = px_w_m * px_h_m
print(f"  Resolução cálculo: {px_w_m:.1f} x {px_h_m:.1f} m/pixel ({calc_w}x{calc_h})")
print(f"  Área pixel: {pixel_area_m2:.0f} m²")

# Área verde por pixel (m²)
green_m2 = green_frac * pixel_area_m2

# Kernel circular (elíptico para compensar pixels não-quadrados)
radius_px_x = int(round(RADIUS_M / px_w_m))
radius_px_y = int(round(RADIUS_M / px_h_m))
print(f"  Kernel: raio {radius_px_x}px (x) × {radius_px_y}px (y) para {RADIUS_M}m")

ky, kx = np.ogrid[-radius_px_y : radius_px_y + 1, -radius_px_x : radius_px_x + 1]
kernel = ((kx * px_w_m) ** 2 + (ky * px_h_m) ** 2 <= RADIUS_M**2).astype(np.float64)
print(f"  Kernel shape: {kernel.shape}, pixels activos: {kernel.sum():.0f}")

# Focal sums
green_500m = ndimage.convolve(green_m2, kernel, mode="constant", cval=0.0)
# GHS-POP nativo ~100m: ao renderizar a ~6.5m, cada célula é replicada em ~N sub-pixels.
# Corrigir dividindo pelo rácio de áreas para obter pop real por pixel de display.
POP_NATIVE_RES = 100  # metros (resolução nativa GHS-POP)
pop_oversampling = (POP_NATIVE_RES**2) / pixel_area_m2
pop_corrected = pop_upscaled / pop_oversampling
print(
    f"  Correccao oversampling pop: /{pop_oversampling:.0f} (nativo {POP_NATIVE_RES}m para {px_w_m:.1f}m)"
)
pop_500m = ndimage.convolve(pop_corrected, kernel, mode="constant", cval=0.0)

# Acessibilidade = verde / pop (m²/hab)
# Filtro: excluir pixels sem população significativa no raio de 500m
# Usa pop_500m (não pop_upscaled local) para não esconder jardins/parques
# cujo pixel GHS-POP é 0 mas têm residentes nas imediações
POP_500M_MIN = 50  # hab mínimos no raio de 500m
accessibility = np.where(pop_500m >= POP_500M_MIN, green_500m / pop_500m, np.nan)

# Cache arrays para análises derivadas (ex: conversão verde pago/privado)
np.save(os.path.join(LAYERS_DIR, "pop_corrected.npy"), pop_corrected)
np.save(os.path.join(LAYERS_DIR, "green_m2.npy"), green_m2)
np.save(os.path.join(LAYERS_DIR, "green_500m.npy"), green_500m)
np.save(os.path.join(LAYERS_DIR, "pop_500m.npy"), pop_500m)
np.save(os.path.join(LAYERS_DIR, "accessibility.npy"), accessibility)
np.save(os.path.join(LAYERS_DIR, "kernel_2sfca.npy"), kernel)
np.savez(
    os.path.join(LAYERS_DIR, "calc_params.npz"),
    pixel_area_m2=pixel_area_m2,
    POP_500M_MIN=POP_500M_MIN,
    px_w_m=px_w_m,
    px_h_m=px_h_m,
    calc_w=calc_w,
    calc_h=calc_h,
)
print("  Arrays 2SFCA guardados em cache (.npy/.npz)")

valid = ~np.isnan(accessibility)
print(
    f"  Acessibilidade: min={np.nanmin(accessibility):.1f}, "
    f"median={np.nanmedian(accessibility):.1f}, "
    f"max={np.nanmax(accessibility):.1f} m²/hab"
)
print(f"  Pixels com pop: {valid.sum()} / {accessibility.size}")

# Limiar OMS
pct_below_9 = (accessibility[valid] < 9).sum() / valid.sum() * 100
print(f"  Abaixo do limiar OMS (9 m²/hab): {pct_below_9:.1f}%")

# ===== Phase 4: Colorir acessibilidade =====
print("\nA colorir mapa de acessibilidade...")

# Paleta divergente: cinzento → vermelho escuro → vermelho → laranja → amarelo → verde
# Classes refinadas no extremo baixo para mostrar influência de parques pequenos
CLASSES = [
    (0, 3, np.array([183, 28, 28])),  # vermelho — défice crítico
    (3, 9, np.array([232, 168, 56])),  # laranja — insuficiente
    (9, 999, np.array([46, 125, 50])),  # verde — adequado
]

# Criar imagem RGBA na resolução de cálculo
acc_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
for lo, hi, color in CLASSES:
    mask = valid & (accessibility >= lo) & (accessibility < hi)
    acc_rgba[mask, 0:3] = color
    acc_rgba[mask, 3] = 255

# Máscara do município do Porto (clipar resultados ao concelho)
print("  A aplicar mascara do municipio...")
muni_gdf = gpd.read_file(PDM_LOCAL, layer="PO_QSFUNCIONAL_PL").to_crs(epsg=4326)
porto_boundary = muni_gdf.union_all()
porto_mask = contains_xy(porto_boundary, *coords_flat).reshape(calc_h, calc_w)
np.save(os.path.join(LAYERS_DIR, "porto_mask.npy"), porto_mask)
# Apagar pixels fora do Porto
acc_rgba[~porto_mask, 3] = 0
print(f"  Pixels fora do Porto removidos: {(~porto_mask).sum()}")

# ===== Estatísticas populacionais por classe =====
print("\nEstatísticas populacionais por classe de acessibilidade:")
porto_valid = valid & porto_mask
low_density = porto_mask & (pop_upscaled <= 10)
total_pop_porto = pop_corrected[porto_mask].sum()
print(f"  População total (GHS-POP): {total_pop_porto:.0f} hab")
for lo, hi, label in [
    (0, 3, "Défice crítico (0–3)"),
    (3, 9, "Insuficiente (3–9)"),
    (9, 999, "Adequado (>9)"),
]:
    mask_cls = porto_valid & (accessibility >= lo) & (accessibility < hi)
    pop_cls = pop_corrected[mask_cls].sum()
    print(f"  {label}: {pop_cls:.0f} hab ({pop_cls / total_pop_porto * 100:.1f}%)")
pop_low = pop_corrected[low_density & ~porto_valid].sum()
print(f"  Baixa densidade: {pop_low:.0f} hab ({pop_low / total_pop_porto * 100:.1f}%)")

# Já está na resolução de display
acc_img_display = Image.fromarray(acc_rgba)

acc_path = os.path.join(LAYERS_DIR, "acessibilidade_2sfca.png")
acc_img_display.save(acc_path)
print(f"  acessibilidade_2sfca.png guardado ({os.path.getsize(acc_path) // 1024} KB)")

# ===== Phase 4b: Máscara de baixa densidade (pop ≤ 10 hab/pixel nativo) =====
lowpop_path = os.path.join(LAYERS_DIR, "baixa_densidade.png")
if not os.path.exists(lowpop_path):
    print("  A gerar máscara de baixa densidade...")
    low_pop_mask = porto_mask & (pop_upscaled <= 10)
    # Remover manchas < 10 ha
    MIN_AREA_HA = 10
    min_pixels = int(MIN_AREA_HA * 10_000 / pixel_area_m2)
    labeled, n_features = ndimage.label(low_pop_mask)
    for i in range(1, n_features + 1):
        if (labeled == i).sum() < min_pixels:
            low_pop_mask[labeled == i] = False
    print(
        f"  Removidas {n_features - ndimage.label(low_pop_mask)[1]} manchas < {MIN_AREA_HA} ha (min {min_pixels} px)"
    )
    # Arredondar contornos: blur + threshold (remove degraus pixelizados)
    mask_float = low_pop_mask.astype(np.float64)
    mask_smooth = ndimage.gaussian_filter(mask_float, sigma=4)
    mask_rounded = mask_smooth > 0.5  # threshold → contornos curvos mas nítidos
    mask_rounded &= porto_mask
    low_pop_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
    low_pop_rgba[mask_rounded] = [200, 200, 200, 204]  # cinza claro, 80% opaco
    Image.fromarray(low_pop_rgba).save(lowpop_path)
    print(f"  baixa_densidade.png guardado ({low_pop_mask.sum()} pixels)")
else:
    print("  baixa_densidade.png já existe, a saltar...")

# ===== Phase 4c: Proximidade 300m (Konijnendijk 3-30-300) =====
# Para cada pixel habitado: existe um parque ≥0,4 ha a ≤300 m?
PROX_RADIUS_M = 300
PARK_MIN_AREA_M2 = 4_000  # 0.4 ha
prox_path = os.path.join(LAYERS_DIR, "proximidade_300m.png")
if not os.path.exists(prox_path) or parques_changed:
    print("\nA calcular proximidade 300m (Konijnendijk)...")
    # Filtrar parques com área ≥0,4 ha
    parques_grandes = parques_gdf[
        parques_gdf.geometry.area * (M_PER_DEG_LAT * M_PER_DEG_LON) >= PARK_MIN_AREA_M2
    ]
    print(f"  Parques >=0.4 ha: {len(parques_grandes)} de {len(parques_gdf)}")
    if len(parques_grandes) > 0:
        parques_grandes_union = parques_grandes.geometry.union_all()
        # Máscara binária dos parques grandes
        inside_grandes = contains_xy(parques_grandes_union, *coords_flat).reshape(
            grid_h, grid_w
        )
        grandes_binary = inside_grandes.astype(np.float64)
        # Kernel circular de 300m
        prox_rx = int(round(PROX_RADIUS_M / px_w_m))
        prox_ry = int(round(PROX_RADIUS_M / px_h_m))
        ky2, kx2 = np.ogrid[-prox_ry : prox_ry + 1, -prox_rx : prox_rx + 1]
        kernel_300 = (
            (kx2 * px_w_m) ** 2 + (ky2 * px_h_m) ** 2 <= PROX_RADIUS_M**2
        ).astype(np.float64)
        print(
            f"  Kernel 300m: {kernel_300.shape}, {kernel_300.sum():.0f} pixels activos"
        )
        # Convolução: se > 0, existe parque ≥0,5ha a ≤300m
        reach_300 = (
            ndimage.convolve(grandes_binary, kernel_300, mode="constant", cval=0.0) > 0
        )
        # Apenas pixels dentro do Porto e com população
        coberto = reach_300 & porto_mask
        nao_coberto = ~reach_300 & porto_mask
        # Estatísticas populacionais
        pop_coberto = pop_corrected[coberto].sum()
        pop_nao_coberto = pop_corrected[nao_coberto].sum()
        pct_coberto = pop_coberto / total_pop_porto * 100
        pct_nao_coberto = pop_nao_coberto / total_pop_porto * 100
        print(
            f"  A <=300m de parque >=0.4ha: {pop_coberto:.0f} hab ({pct_coberto:.1f}%)"
        )
        print(
            f"  A >300m de parque >=0.4ha: {pop_nao_coberto:.0f} hab ({pct_nao_coberto:.1f}%)"
        )
        # PNG: verde onde coberto, vermelho onde não coberto (só pixels habitados)
        prox_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
        habitado = porto_mask & (pop_500m >= POP_500M_MIN)
        prox_rgba[habitado & coberto] = [46, 125, 50, 255]  # verde (#2E7D32)
        prox_rgba[habitado & ~coberto] = [183, 28, 28, 255]  # vermelho (#B71C1C)
        Image.fromarray(prox_rgba).save(prox_path)
        print(
            f"  proximidade_300m.png guardado ({os.path.getsize(prox_path) // 1024} KB)"
        )
        # Cache arrays de proximidade para análises derivadas
        np.save(os.path.join(LAYERS_DIR, "kernel_300.npy"), kernel_300)
        np.save(os.path.join(LAYERS_DIR, "reach_300.npy"), reach_300)
        print("  Arrays proximidade 300m guardados em cache (.npy)")
    else:
        print("  AVISO: nenhum parque >=0.4 ha encontrado")
        prox_rgba = np.zeros((calc_h, calc_w, 4), dtype=np.uint8)
        Image.fromarray(prox_rgba).save(prox_path)
else:
    print(f"\nProximidade 300m: a reutilizar {prox_path}")

# ===== Phase 5: Municipios (reutilizar ou descarregar) =====
muni_path = os.path.join(PARENT_LAYERS, "municipios.png")
if not os.path.exists(muni_path):
    print("\nA descarregar limites municipais...")
    muni_styled = (
        ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=3)
    )
    download_mono_layer(
        muni_styled, "444444", "municipios.png", porto, DIM, PARENT_LAYERS
    )
else:
    print(f"\nMunicípios: a reutilizar {muni_path}")


# ===== Phase 6: HTML =====
# Guardar hash actualizado (só depois de todas as fases completarem com sucesso)
_cache_state['parques_hash'] = _parques_hash
with open(CACHE_STATE_PATH, 'w') as _f:
    json.dump(_cache_state, _f)

print("\nA construir mapa...")
build_html(SCRIPT_DIR, LAYERS_DIR, PARENT_LAYERS, BOUNDS,
           verde_pub_path, verde_pago_path, acc_path, lowpop_path,
           muni_path, prox_path)
