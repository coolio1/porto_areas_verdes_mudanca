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
import requests
import os
import base64
import io
import math
import time
import numpy as np
from PIL import Image
from scipy import ndimage
from dotenv import load_dotenv

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

# ===== Sentinel-2 — classificação verde (2024-25) =====
BANDS = ["B3", "B4", "B8", "B11", "SCL"]


def getS2col(start, end):
    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(porto)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 30))
        .select(BANDS)
    )

    def process(img):
        scl = img.select("SCL")
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("ndvi")
        ndbi = img.normalizedDifference(["B11", "B8"]).rename("ndbi")
        nir_green = img.select("B8").divide(img.select("B3").max(1)).rename("nir_green")
        green = img.select("B3").rename("green")
        return ndvi.addBands(ndbi).addBands(nir_green).addBands(green).updateMask(clear)

    return s2.map(process)


def getComposite(years):
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])
    for year in years:
        full = getS2col(f"{year}-05-01", f"{year}-10-31")
        all_col = all_col.merge(full)
        spring = getS2col(f"{year}-05-15", f"{year}-06-30")
        spring_col = spring_col.merge(spring)
    median = all_col.median().clip(porto)
    spring_ndvi = (
        spring_col.select("ndvi")
        .reduce(ee.Reducer.percentile([15]))
        .rename("spring_ndvi")
        .clip(porto)
    )
    ndvi_min = (
        all_col.select("ndvi")
        .reduce(ee.Reducer.percentile([10]))
        .rename("ndvi_min")
        .clip(porto)
    )
    return median.addBands(spring_ndvi).addBands(ndvi_min)


esa = ee.Image("ESA/WorldCover/v200/2021").select("Map").clip(porto)
esaBuilt = esa.eq(50)


def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min):
    b3_ok = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isTreeStrict = (
        ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok)
    )
    b3_ok_mixed = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (
        ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTreeStrict.Not())
    )
    isTree = isTreeStrict.Or(isMixed)
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isBuilt, isSolo


print("A calcular composito Sentinel-2 (2024-25)...")
s2_late = getComposite([2024, 2025])
ndvi_l = s2_late.select("ndvi")
ndbi_l = s2_late.select("ndbi")
nirgreen_l = s2_late.select("nir_green")
green_l = s2_late.select("green")
spring_ndvi_l = s2_late.select("spring_ndvi")
ndvi_min_l = s2_late.select("ndvi_min")

isTree_l, isBuilt_l, isSolo_l = classify(
    ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l
)
isGreen_l = isTree_l.Or(isSolo_l)  # árvores + solo/relva

# GHS-POP 2020 (densidade pop 100m)
ghspop = ee.Image("JRC/GHSL/P2023A/GHS_POP/2020").select("population_count").clip(porto)

print("Classificação concluída.")


# ===== Download helpers =====
def download_mono_layer(image, color_hex, filename, layers_dir=LAYERS_DIR):
    """Download camada monocromática com transparência."""
    filepath = os.path.join(layers_dir, filename)
    if os.path.exists(filepath):
        print(f"  {filename} já existe, a saltar...")
        return filepath
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    for attempt in range(3):
        url = vis.getThumbURL({"region": porto, "dimensions": DIM, "format": "png"})
        print(f"  A descarregar {filename}...")
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            break
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(3)
            else:
                return None
    arr = np.array(img)
    dark = (arr[:, :, 0] < 10) & (arr[:, :, 1] < 10) & (arr[:, :, 2] < 10)
    arr[dark, 3] = 0
    Image.fromarray(arr).save(filepath)
    print(f"  {filename} guardado ({os.path.getsize(filepath) // 1024} KB)")
    return filepath


def download_greyscale(image, dim, min_val, max_val, label):
    """Download imagem GEE como array numpy float via greyscale PNG."""
    vis = image.unmask(0).visualize(
        min=min_val, max=max_val, palette=["000000", "FFFFFF"]
    )
    for attempt in range(3):
        url = vis.getThumbURL({"region": porto, "dimensions": dim, "format": "png"})
        print(f"  A descarregar {label} ({dim}px)...")
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert("L")
            arr = np.array(img).astype(np.float64) / 255.0 * max_val
            print(f"  {label}: {arr.shape}, min={arr.min():.1f}, max={arr.max():.1f}")
            return arr
        except Exception as e:
            print(f"  Tentativa {attempt + 1} falhou: {e}")
            if attempt < 2:
                time.sleep(3)
    return None


# ===== Phase 1: Download verde total (display) =====
print("\nA descarregar verde total (display)...")
verde_total_path = os.path.join(LAYERS_DIR, "verde_total.png")
download_mono_layer(isGreen_l.selfMask(), "2E7D32", "verde_total.png")

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
    "Área verde associada a equipamento",
    "Área de frente atlântica e ribeirinha",
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

# Grid de coordenadas (reutilizado por ambas as camadas)
img_ref = Image.open(verde_total_path).convert("RGBA")
grid_w, grid_h = img_ref.size
xs = np.linspace(LON_MIN, LON_MAX, grid_w)
ys = np.linspace(LAT_MAX, LAT_MIN, grid_h)
xx, yy = np.meshgrid(xs, ys)
coords_flat = (xx.ravel(), yy.ravel())

# --- Verde público: Sentinel-2 verde ∩ parques oficiais ---
# Pixels dentro dos parques sem verde Sentinel-2 são pintados com verde sólido
# (jardins pequenos/urbanos onde a copa não domina o pixel)
verde_pub_path = os.path.join(LAYERS_DIR, "verde_publico.png")
if not os.path.exists(verde_pub_path):
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

# --- Estratégia de expansão (CMP) ---
expansao_path = os.path.join(SCRIPT_DIR, "expansao_verde.geojson")
expansao_union = None
if os.path.exists(expansao_path):
    expansao_gdf = gpd.read_file(expansao_path).to_crs(epsg=4326)
    expansao_union = expansao_gdf.geometry.union_all()
    print(f"  {len(expansao_gdf)} espaços de expansão carregados")

# --- Verde pago ou não usufruível: polígonos PDM \ parques \ expansão (sólido) ---
verde_pago_path = os.path.join(LAYERS_DIR, "verde_pago.png")
if not os.path.exists(verde_pago_path):
    print("  A calcular verde pago (PDM fora dos parques e expansão, sólido)...")
    pdm_minus_parques = pdm_verde_union.difference(parques_union)
    if expansao_union is not None:
        pdm_minus_parques = pdm_minus_parques.difference(expansao_union)
    inside_pago = contains_xy(pdm_minus_parques, *coords_flat).reshape(grid_h, grid_w)
    pago_arr = np.zeros((grid_h, grid_w, 4), dtype=np.uint8)
    pago_arr[inside_pago, 3] = 255
    Image.fromarray(pago_arr).save(verde_pago_path)
    n_pago = inside_pago.sum()
    print(f"  verde_pago.png guardado ({n_pago} pixels)")
else:
    print("  verde_pago.png já existe, a saltar...")

# --- Camada de expansão ---
verde_exp_path = os.path.join(LAYERS_DIR, "verde_expansao.png")
if not os.path.exists(verde_exp_path):
    if expansao_union is not None:
        print("  A gerar camada de expansão...")
        # Expansão \ parques actuais (evitar sobreposição)
        exp_minus_parques = expansao_union.difference(parques_union)
        inside_exp = contains_xy(exp_minus_parques, *coords_flat).reshape(
            grid_h, grid_w
        )
        exp_arr = np.zeros((grid_h, grid_w, 4), dtype=np.uint8)
        exp_arr[inside_exp, 3] = 255
        Image.fromarray(exp_arr).save(verde_exp_path)
        print(f"  verde_expansao.png guardado ({inside_exp.sum()} pixels)")
    else:
        print("  AVISO: expansao_verde.geojson não encontrado — sem camada de expansão")
else:
    print("  verde_expansao.png já existe, a saltar...")

# ===== Phase 3: 2SFCA (cálculo a ~30m) =====
print("\nA calcular 2SFCA (300m)...")

# Obter valor máximo de população para normalização
print("  A consultar GHS-POP max...")
pop_max_info = ghspop.reduceRegion(ee.Reducer.max(), porto, 100).getInfo()
POP_MAX = pop_max_info["population_count"]
print(f"  GHS-POP max: {POP_MAX:.1f} hab/pixel")

# Download arrays de cálculo
pop_arr = download_greyscale(ghspop, CALC_DIM, 0, POP_MAX, "GHS-POP calc")

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

# ===== Phase 5: Municipios (reutilizar ou descarregar) =====
muni_path = os.path.join(PARENT_LAYERS, "municipios.png")
if not os.path.exists(muni_path):
    print("\nA descarregar limites municipais...")
    muni_styled = (
        ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=3)
    )
    download_mono_layer(
        muni_styled, "444444", "municipios.png", layers_dir=PARENT_LAYERS
    )
else:
    print(f"\nMunicípios: a reutilizar {muni_path}")

# ===== Phase 6: HTML =====
print("\nA construir mapa...")


def to_base64(filepath):
    with open(filepath, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


# Camadas
verde_pub_b64 = to_base64(verde_pub_path)
verde_priv_b64 = to_base64(os.path.join(PARENT_LAYERS, "interior_subsistente.png"))
verde_pago_b64 = to_base64(verde_pago_path)
verde_exp_b64 = to_base64(verde_exp_path) if os.path.exists(verde_exp_path) else ""
ghspop_b64 = to_base64(os.path.join(PARENT_LAYERS, "ghspop.png"))
acc_b64 = to_base64(acc_path)
lowpop_b64 = to_base64(lowpop_path)
muni_b64 = to_base64(muni_path)

# Carregar GeoJSON dos parques nomeados (se existir)
parques_geojson_path = os.path.join(SCRIPT_DIR, "parques_porto.geojson")
parques_geojson_str = ""
if os.path.exists(parques_geojson_path):
    with open(parques_geojson_path, "r", encoding="utf-8") as f:
        parques_geojson_str = f.read()
    import json as _json

    _pdata = _json.loads(parques_geojson_str)
    print(f"  Parques nomeados: {len(_pdata['features'])} carregados")
else:
    print(
        "  AVISO: parques_porto.geojson não encontrado — correr criar_parques.py primeiro"
    )

# Carregar GeoJSON da expansão (para contornos e etiquetas no mapa)
expansao_geojson_str = ""
if os.path.exists(expansao_path):
    with open(expansao_path, "r", encoding="utf-8") as f:
        expansao_geojson_str = f.read()

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
        "Satélite",
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
<title>Acessibilidade a Verde P&uacute;blico — Porto</title>
<meta name="description" content="Mapa de acessibilidade da população do Porto a espaços verdes públicos (m²/hab, raio 500m), usando o método 2SFCA com dados GHS-POP e PDM.">
<link rel="canonical" href="https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/acessibilidade_verde.html">
<meta property="og:title" content="Acessibilidade a Verde Público — Porto">
<meta property="og:description" content="Acessibilidade da população a espaços verdes públicos no Porto (m²/hab, raio 500m), método 2SFCA.">
<meta property="og:url" content="https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/acessibilidade_verde.html">
<meta property="og:type" content="website">
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
  #nav a.active {{ background:#2E7D32; color:#fff; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:260px;
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
  .exp-label {{ background:rgba(255,255,255,0.85)!important; border:none!important; box-shadow:0 1px 3px rgba(0,0,0,0.2); font:10px 'Segoe UI',Arial,sans-serif; color:#00695C; padding:1px 5px; border-radius:3px; font-style:italic; }}
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
  <a href="acessibilidade_verde.html" class="active">Acessibilidade</a>
  <a href="../atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <button id="panel-toggle" onclick="var p=document.getElementById('panel');p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'&#9650; Abrir legenda':'&#9660; Fechar';">&#9660; Fechar</button>
  <div class="panel-body">
  <b style="font-size:14px;">Acessibilidade a Verde P&uacute;blico</b>

  <div id="acc-legend" style="display:block;margin:4px 0 8px 0;">
    <div class="section">Acessibilidade (m&sup2;/hab, raio 500m)</div>
    <div style="font-size:10px;color:#888;margin-bottom:2px;">m&sup2;/hab (raio 500m)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">0 &ndash; 3 (d&eacute;fice cr&iacute;tico)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#E8A838;display:inline-block;"></span>
        <span style="color:#666;">3 &ndash; 9 (insuficiente)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">&gt;9 (adequado)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;margin-top:2px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#C8C8C8;display:inline-block;"></span>
        <span style="color:#666;">Baixa densidade</span>
      </div>
    </div>
    <div style="color:#aaa;font-size:9px;margin-top:4px;">OMS recomenda &ge;9 m&sup2;/hab</div>
  </div>

  <div class="section">Camadas</div>
  <div id="layer-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Contexto</div>
  <div id="bg-rows"></div>
  <div id="pop-legend" style="display:none;margin:4px 0 0 22px;">
    <div style="font-size:10px;color:#888;margin-bottom:2px;">hab/pixel (100m)</div>
    <div style="display:flex;align-items:center;gap:4px;">
      <span style="font-size:9px;color:#888;">0</span>
      <div style="width:120px;height:10px;border-radius:3px;background:linear-gradient(to right,#f5e6d0,#d4b896,#b08a5e,#8b6934,#6b4a1e,#4a2f0a);"></div>
      <span style="font-size:9px;color:#888;">150+</span>
    </div>
  </div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#ddd;margin:10px 0 4px 0;">
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; GHS-POP 100m (JRC)<br>
  47 parques e jardins (CMP + OSM)<br>
  M&eacute;todo: Two-Step Floating Catchment Area</span>
  </div>
</div>

<script>
var parquesData = {parques_geojson_str if parques_geojson_str else "null"};
var expansaoData = {expansao_geojson_str if expansao_geojson_str else "null"};
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {BOUNDS};

// Camada de acessibilidade (pré-colorida, 70% opacidade, on por defeito)
var accLayer = {{
  id: "acessibilidade",
  label: "Acessibilidade a 500m",
  src: "{acc_b64}",
  opacity: 0.7,
  show: true
}};

// Máscara de baixa densidade (cinza claro, topo de tudo)
var lowPopLayer = {{
  id: "baixa_densidade",
  label: "Baixa densidade",
  src: "{lowpop_b64}",
  show: true
}};

// Verde público raster (usado dentro da camada combinada "Parques e Jardins")
var greenLayer = {{
  id: "verde_publico",
  color: "#2E7D32",
  src: "{verde_pub_b64}",
}};

// Camada de verde privado (monocromática azul)
var greenPrivLayer = {{
  id: "verde_privado",
  label: "Verde privado",
  color: "#1565C0",
  src: "{verde_priv_b64}",
  show: false
}};

// Camada de verde pago ou não usufruível — castanho
var outroVerdeLayer = {{
  id: "verde_pago",
  label: "Verde pago ou n\\u00e3o usufru\\u00edvel",
  color: "#8D6E63",
  src: "{verde_pago_b64}",
  show: false
}};

// Estratégia de expansão (CMP) — azul-esverdeado
var expansaoLayer = {{
  id: "verde_expansao",
  label: "Estrat\\u00e9gia de expans\\u00e3o (CMP)",
  color: "#00897B",
  src: "{verde_exp_b64}",
  show: false
}};

// Limites municipais
var muniLayer = {{
  id: "municipios",
  label: "Limites municipais",
  color: "#444444",
  src: "{muni_b64}",
  show: true
}};

// Contexto: densidade populacional
var bgLayer = {{
  id: "ghspop",
  label: "Densidade populacional",
  src: "{ghspop_b64}",
  opacity: 0.7,
  show: false
}};

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
  // Pane para camada de fundo (z-index baixo)
  map.createPane('bgPane');
  map.getPane('bgPane').style.zIndex = 250;

  // Pane para acessibilidade (topo)
  map.createPane('accPane');
  map.getPane('accPane').style.zIndex = 450;

  // --- Camada de fundo: densidade pop ---
  var bgOverlay = L.imageOverlay(bgLayer.src, bounds, {{opacity: bgLayer.opacity, pane: 'bgPane'}});
  if (bgLayer.show) bgOverlay.addTo(map);
  var bgDiv = document.getElementById('bg-rows');
  var bgRow = document.createElement('div'); bgRow.className = 'row';
  var bgCb = document.createElement('input'); bgCb.type = 'checkbox'; bgCb.checked = bgLayer.show;
  bgCb.addEventListener('change', function() {{
    if (this.checked) {{ bgOverlay.addTo(map); document.getElementById('pop-legend').style.display='block'; }}
    else {{ map.removeLayer(bgOverlay); document.getElementById('pop-legend').style.display='none'; }}
  }});
  var bgLb = document.createElement('label'); bgLb.textContent = bgLayer.label; bgLb.style.fontSize='12px';
  bgRow.appendChild(bgCb); bgRow.appendChild(bgLb); bgDiv.appendChild(bgRow);

  // --- Camadas principais ---
  var monoLayers = [greenPrivLayer, outroVerdeLayer, muniLayer];
  var div = document.getElementById('layer-rows');
  var overlays = [];

  for (var i = 0; i < monoLayers.length; i++) {{
    var L_ = monoLayers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    overlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) overlays[idx].addTo(map); else map.removeLayer(overlays[idx]);
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    div.appendChild(row);
  }}

  // --- Acessibilidade (topo, pré-colorida) ---
  var accOverlay = L.imageOverlay(accLayer.src, bounds, {{opacity: accLayer.opacity, pane: 'accPane'}});
  if (accLayer.show) accOverlay.addTo(map);

  var accRow = document.createElement('div'); accRow.className = 'row';
  var accCb = document.createElement('input'); accCb.type = 'checkbox'; accCb.checked = accLayer.show;
  accCb.addEventListener('change', function() {{
    if (this.checked) {{
      accOverlay.addTo(map);
      if (window._lowPopOverlay) window._lowPopOverlay.addTo(map);
    }} else {{
      map.removeLayer(accOverlay);
      if (window._lowPopOverlay) map.removeLayer(window._lowPopOverlay);
    }}
  }});
  var accSw = document.createElement('span'); accSw.className = 'swatch';
  accSw.style.background = 'linear-gradient(to right, #880E0E, #B71C1C, #E53935, #E8A838, #FFD700, #8BC34A, #2E7D32)';
  var accLb = document.createElement('label'); accLb.textContent = accLayer.label; accLb.style.fontSize = '12px';
  accRow.appendChild(accCb); accRow.appendChild(accSw); accRow.appendChild(accLb);
  // Acessibilidade no topo
  div.insertBefore(accRow, div.firstChild);

  // --- Camada combinada "Parques e Jardins" (raster verde + contornos GeoJSON) ---
  // Pane no topo de tudo, opaco
  map.createPane('parquesPane');
  map.getPane('parquesPane').style.zIndex = 550;

  // Raster: verde público (Sentinel-2 dentro dos parques)
  var greenMask = await extractMask(greenLayer.src);
  var greenSrc = renderColored(greenMask, greenLayer.color);
  var greenOverlay = L.imageOverlay(greenSrc, bounds, {{pane: 'parquesPane'}});
  greenOverlay.addTo(map);

  // Contornos GeoJSON dos parques
  var parquesGeoLayer = null;
  if (parquesData) {{

    parquesGeoLayer = L.geoJson(parquesData, {{
      pane: 'parquesPane',
      style: function(f) {{
        return {{
          color: '#1B5E20', weight: 2.5, opacity: 0.9,
          fillColor: '#2E7D32', fillOpacity: 0.08,
          dashArray: f.properties.fonte === 'manual' ? '4 4' : null
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var area = p.area_ha ? p.area_ha + ' ha (oficial)' : p.area_calc_ha + ' ha (calc.)';
        var html = '<b style="font-size:13px;">' + p.nome + '</b><br>';
        html += '<span style="color:#666;">' + (p.tipo || '') + ' &mdash; ' + area + '</span>';
        layer.bindPopup(html);
        layer.bindTooltip(p.nome, {{
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
      labels.forEach(function(l) {{ l.style.display = z >= 14 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }}

  // Checkbox único para raster + contornos
  var pRow = document.createElement('div'); pRow.className = 'row';
  var pCb = document.createElement('input'); pCb.type = 'checkbox'; pCb.checked = true;
  pCb.addEventListener('change', function() {{
    if (this.checked) {{
      greenOverlay.addTo(map);
      if (parquesGeoLayer) parquesGeoLayer.addTo(map);
    }} else {{
      map.removeLayer(greenOverlay);
      if (parquesGeoLayer) map.removeLayer(parquesGeoLayer);
    }}
  }});
  var pSw = document.createElement('span'); pSw.className = 'swatch'; pSw.style.backgroundColor = '#2E7D32';
  var pLb = document.createElement('label'); pLb.textContent = 'Parques e Jardins'; pLb.style.fontSize = '12px';
  pRow.appendChild(pCb); pRow.appendChild(pSw); pRow.appendChild(pLb);
  div.insertBefore(pRow, accRow.nextSibling);

  // --- Camada GeoJSON de expansão (contornos + etiquetas) ---
  var expansaoGeoLayer = null;
  if (expansaoData) {{
    map.createPane('expansaoGeoPane');
    map.getPane('expansaoGeoPane').style.zIndex = 525;

    expansaoGeoLayer = L.geoJson(expansaoData, {{
      pane: 'expansaoGeoPane',
      style: function(f) {{
        return {{
          color: '#00695C', weight: 2, opacity: 0.9,
          fillColor: '#00897B', fillOpacity: 0.08,
          dashArray: f.properties.fonte === 'manual' ? '4 4' : null
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var html = '<b style="font-size:13px;">' + p.nome + '</b><br>';
        html += '<span style="color:#666;">Expans\\u00e3o planeada &mdash; ' + p.area_ha_planeada + ' ha</span>';
        layer.bindPopup(html);
        layer.bindTooltip(p.nome, {{
          permanent: true, direction: 'center',
          className: 'exp-label',
          offset: [0, 0]
        }});
      }}
    }});

    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.exp-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 14 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }}

  // Raster de expansão (mesma pane que GeoJSON)
  var expRasterOverlay = null;
  if (expansaoLayer.src) {{
    var expMask = await extractMask(expansaoLayer.src);
    var expSrc = renderColored(expMask, expansaoLayer.color);
    expRasterOverlay = L.imageOverlay(expSrc, bounds, {{pane: 'expansaoGeoPane'}});
  }}

  // Checkbox para expansão (raster + contornos)
  var eRow = document.createElement('div'); eRow.className = 'row';
  var eCb = document.createElement('input'); eCb.type = 'checkbox'; eCb.checked = false;
  eCb.addEventListener('change', function() {{
    if (this.checked) {{
      if (expRasterOverlay) expRasterOverlay.addTo(map);
      if (expansaoGeoLayer) expansaoGeoLayer.addTo(map);
    }} else {{
      if (expRasterOverlay) map.removeLayer(expRasterOverlay);
      if (expansaoGeoLayer) map.removeLayer(expansaoGeoLayer);
    }}
  }});
  var eSw = document.createElement('span'); eSw.className = 'swatch'; eSw.style.backgroundColor = '#00897B';
  var eLb = document.createElement('label'); eLb.textContent = 'Estrat\\u00e9gia de expans\\u00e3o (CMP)'; eLb.style.fontSize = '12px';
  eRow.appendChild(eCb); eRow.appendChild(eSw); eRow.appendChild(eLb);
  div.insertBefore(eRow, pRow.nextSibling);

  // --- Baixa densidade (acima da acessibilidade, abaixo dos parques) ---
  map.createPane('lowPopPane');
  map.getPane('lowPopPane').style.zIndex = 475;
  var lowPopOverlay = L.imageOverlay(lowPopLayer.src, bounds, {{pane: 'lowPopPane'}});
  window._lowPopOverlay = lowPopOverlay;
  if (accLayer.show) lowPopOverlay.addTo(map);
}}

init();
</script>
<div id="credit" style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
<script>if(window.innerWidth<=768){{var p=document.getElementById('panel'),b=document.getElementById('panel-toggle');p.classList.add('collapsed');b.textContent='\\u25B2 Abrir legenda';}}</script>
</body>
</html>'''

output = os.path.join(SCRIPT_DIR, "acessibilidade_verde.html")
with open(output, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nMapa guardado: {output}")
print(f"Abrir no browser: file:///{output.replace(os.sep, '/')}")
