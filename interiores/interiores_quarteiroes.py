import ee
import requests
import os
import io
import sys
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LAYERS_DIR = os.path.join(ROOT_DIR, "layers")

sys.path.insert(0, os.path.join(ROOT_DIR, "acessibilidade"))
from acessibilidade_gee import getS2col, getComposite, classify
from interiores_html import build_html

load_dotenv(os.path.join(ROOT_DIR, ".env"))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

porto = ee.Geometry.Polygon(
    [[[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]]
)
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]
DIM = 2048

municipios = ee.FeatureCollection(f"projects/{GEE_PROJECT}/assets/CAOP2025_municipios")
municipiosPorto = municipios.filterBounds(porto)

print("A calcular compositos Sentinel-2...")
s2_early = getComposite([2016, 2017], porto)
s2_late = getComposite([2024, 2025], porto)

# ESA WorldCover 10m (2021) como desempate
esa = ee.Image("ESA/WorldCover/v200/2021").select("Map").clip(porto)
esaBuilt = esa.eq(50)


ndvi_e = s2_early.select("ndvi")
ndbi_e = s2_early.select("ndbi")
nirgreen_e = s2_early.select("nir_green")
green_e = s2_early.select("green")
spring_ndvi_e = s2_early.select("spring_ndvi")
ndvi_min_e = s2_early.select("ndvi_min")

ndvi_l = s2_late.select("ndvi")
ndbi_l = s2_late.select("ndbi")
nirgreen_l = s2_late.select("nir_green")
green_l = s2_late.select("green")
spring_ndvi_l = s2_late.select("spring_ndvi")
ndvi_min_l = s2_late.select("ndvi_min")

isTree_e, isBuilt_e, isSolo_e = classify(
    ndvi_e, ndbi_e, nirgreen_e, green_e, spring_ndvi_e, ndvi_min_e, esaBuilt
)
isTree_l_base, isBuilt_l_base, _ = classify(
    ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l, esaBuilt
)

# Persistence rule: built in 2016 stays built unless NDVI 2025 >= 0.45
stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isSolo_l = isTree_l.Not().And(isBuilt_l.Not())

# ----- Zona centro = interior da VCI (Via de Cintura Interna) -----
print("A obter traçado da VCI...")
from shapely.geometry import LineString
from shapely.ops import unary_union as union_geom

VCI_QUERY = """
[out:json][timeout:60];
way["name"="Via de Cintura Interna"](41.13,-8.70,41.19,-8.54);
out body;
>;
out skel qt;
"""

vci_data = None
for overpass_url in [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]:
    for attempt in range(3):
        print(f"  A tentar {overpass_url} (tentativa {attempt + 1})...")
        try:
            resp = requests.get(overpass_url, params={"data": VCI_QUERY}, timeout=90)
            if resp.status_code == 200:
                vci_data = resp.json()
                break
        except Exception:
            pass
        import time as _time

        _time.sleep(5)
    if vci_data:
        break

# Construir nós e segmentos da VCI
vci_nodes = {}
for el in vci_data["elements"]:
    if el["type"] == "node":
        vci_nodes[el["id"]] = (el["lon"], el["lat"])

vci_lines = []
for el in vci_data["elements"]:
    if el["type"] == "way" and "nodes" in el:
        coords = [vci_nodes[n] for n in el["nodes"] if n in vci_nodes]
        if len(coords) >= 2:
            vci_lines.append(LineString(coords))

# Juntar segmentos, buffer para unir as 2 faixas, subtrair ao bbox
from shapely.geometry import Point, box as shapely_box

vci_buffer = union_geom(vci_lines).buffer(0.0003)  # ~30m junta as faixas
porto_box = shapely_box(-8.70, 41.13, -8.54, 41.19)
remaining = porto_box.difference(vci_buffer)

# Encontrar o polígono que contém o centro do Porto
porto_center = Point(-8.61, 41.155)
centro_union = None
if remaining.geom_type == "MultiPolygon":
    for p in remaining.geoms:
        if p.contains(porto_center):
            centro_union = p
            break
elif remaining.geom_type == "Polygon" and remaining.contains(porto_center):
    centro_union = remaining

if centro_union:
    print(f"  Interior da VCI encontrado (área: {centro_union.area:.6f} graus²)")
    ee_coords = [list(centro_union.exterior.coords)]
    centro_ee = ee.Geometry.Polygon(ee_coords)
else:
    print("  AVISO: interior da VCI não encontrado, a usar porto inteiro")
    centro_ee = porto

is_centro = ee.Image.constant(1).clip(centro_ee).unmask(0).clip(porto)

# ----- Camadas base -----
isGreen_l = isTree_l.Or(isSolo_l)
isGreen_e = isTree_e.Or(isSolo_e)

# Descarregar camadas brutas (sem filtros — filtragem feita localmente em vector)
subsistente = isGreen_l.selfMask()
perdido = isGreen_e.And(isBuilt_l).selfMask()

# GHS-POP 2020 (densidade populacional 100m)
print("A preparar camada de densidade populacional (GHS-POP)...")
ghspop = ee.Image("JRC/GHSL/P2023A/GHS_POP/2020").select("population_count").clip(porto)
# Visualizar com paleta quente (transparente onde pop=0)
ghspop_vis = ghspop.updateMask(ghspop.gt(0)).visualize(
    min=0,
    max=150,
    palette=["#f5e6d0", "#d4b896", "#b08a5e", "#8b6934", "#6b4a1e", "#4a2f0a"],
)

print("Classificacao concluida.")

from PIL import Image
import numpy as np
import time

os.makedirs(LAYERS_DIR, exist_ok=True)


def download_layer(image, color_hex, filename):
    filepath = os.path.join(LAYERS_DIR, filename)
    if os.path.exists(filepath):
        print(f"  {filename} ja existe, a saltar...")
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
    img = Image.fromarray(arr)
    img.save(filepath)
    print(f"  {filename} guardado ({os.path.getsize(filepath) // 1024} KB)")
    return filepath


def download_rgb_layer(image, filename):
    """Download pre-visualized RGB layer (e.g., GHS-POP with palette)."""
    filepath = os.path.join(LAYERS_DIR, filename)
    if os.path.exists(filepath):
        print(f"  {filename} ja existe, a saltar...")
        return filepath
    for attempt in range(3):
        url = image.getThumbURL({"region": porto, "dimensions": DIM, "format": "png"})
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
    # Tornar pixels pretos/quase-pretos transparentes
    arr = np.array(img)
    dark = (arr[:, :, 0] < 10) & (arr[:, :, 1] < 10) & (arr[:, :, 2] < 10)
    arr[dark, 3] = 0
    Image.fromarray(arr).save(filepath)
    print(f"  {filename} guardado ({os.path.getsize(filepath) // 1024} KB)")
    return filepath


print("\nA descarregar camadas...")
download_layer(subsistente, "2E7D32", "interior_subsistente.png")
download_layer(perdido, "D7263D", "interior_perdido.png")
download_rgb_layer(ghspop_vis, "ghspop.png")
# Interior VCI: rasterizar contorno localmente (geometria vem do OSM, não do GEE)
centro_path = os.path.join(LAYERS_DIR, "centro_alargado.png")
if not os.path.exists(centro_path) and centro_union is not None:
    print("  A rasterizar contorno da VCI...")
    ref_img = Image.open(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
    W, H = ref_img.size
    centro_boundary = centro_union.boundary
    centro_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    from PIL import ImageDraw

    draw = ImageDraw.Draw(centro_img)
    lon_min, lon_max = -8.70, -8.54
    lat_min, lat_max = 41.13, 41.19

    def geo_to_pixel(lon, lat):
        x = (lon - lon_min) / (lon_max - lon_min) * W
        y = (lat_max - lat) / (lat_max - lat_min) * H
        return (x, y)

    if centro_boundary.geom_type == "MultiLineString":
        lines = centro_boundary.geoms
    else:
        lines = [centro_boundary]
    for line in lines:
        coords = [geo_to_pixel(x, y) for x, y in line.coords]
        if len(coords) >= 2:
            draw.line(coords, fill=(255, 215, 0, 255), width=3)
    centro_img.save(centro_path)
    print(f"  centro_alargado.png guardado ({os.path.getsize(centro_path) // 1024} KB)")
else:
    print("  centro_alargado.png ja existe, a saltar...")

# Municipios (reuse if exists)
muni_styled = (
    ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=3)
)
download_layer(muni_styled, "444444", "municipios.png")


# ----- Phase 2: Subtrair parques e jardins + verde pago -----
import geopandas as gpd
from shapely import contains_xy


def apply_geom_mask(filepath, geom, label):
    """Remove pixels dentro de uma geometria."""
    if geom.is_empty:
        return
    img = Image.open(filepath).convert("RGBA")
    w, h = img.size
    arr = np.array(img)
    xs = np.linspace(-8.70, -8.54, w)
    ys = np.linspace(41.19, 41.13, h)
    xx, yy = np.meshgrid(xs, ys)
    mask = contains_xy(geom, xx.ravel(), yy.ravel()).reshape(h, w)
    n_masked = (arr[:, :, 3] > 0) & mask
    arr[mask, 3] = 0
    Image.fromarray(arr).save(filepath)
    print(
        f"  {os.path.basename(filepath)}: {n_masked.sum()} pixels mascarados ({label})"
    )


def apply_raster_mask(filepath, mask_path, label):
    """Remove pixels que coincidem com outra camada raster."""
    mask_img = Image.open(mask_path).convert("RGBA")
    mask_arr = np.array(mask_img)[:, :, 3] > 0
    img = Image.open(filepath).convert("RGBA")
    arr = np.array(img)
    n_masked = ((arr[:, :, 3] > 0) & mask_arr).sum()
    arr[mask_arr, 3] = 0
    Image.fromarray(arr).save(filepath)
    print(f"  {os.path.basename(filepath)}: {n_masked} pixels mascarados ({label})")


# 2a. Subtrair parques e jardins (inventario)
parques_path = os.path.join("acessibilidade", "parques_porto.geojson")
if os.path.exists(parques_path):
    print("\nA subtrair parques e jardins...")
    parques_gdf = gpd.read_file(parques_path).to_crs(epsg=4326)
    parques_union = parques_gdf.geometry.union_all()
    apply_geom_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), parques_union, "parques")
    apply_geom_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), parques_union, "parques")
    print(f"  {len(parques_gdf)} parques subtraidos.")

# 2b. Subtrair verde pago
verde_pago_path = os.path.join(ROOT_DIR, "acessibilidade", "layers", "verde_pago.png")
if os.path.exists(verde_pago_path):
    print("A subtrair verde pago...")
    apply_raster_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), verde_pago_path, "verde pago")
    apply_raster_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), verde_pago_path, "verde pago")

# ----- Phase 2b: Mascara de estradas (OSM) -----
print("\nA descarregar estradas do OSM...")

ROADS_QUERY = """
[out:json][timeout:90];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|residential|unclassified|service|living_street|pedestrian)$"](41.13,-8.70,41.19,-8.54);
);
out body;
>;
out skel qt;
"""

roads_data = None
for overpass_url in [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]:
    for attempt in range(3):
        print(f"  A tentar {overpass_url} (tentativa {attempt + 1})...")
        try:
            resp = requests.get(overpass_url, params={"data": ROADS_QUERY}, timeout=120)
            if resp.status_code == 200:
                try:
                    roads_data = resp.json()
                    break
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(5)
    if roads_data:
        break

if roads_data:
    road_nodes = {}
    for el in roads_data["elements"]:
        if el["type"] == "node":
            road_nodes[el["id"]] = (el["lon"], el["lat"])

    road_lines = []
    for el in roads_data["elements"]:
        if el["type"] == "way" and "nodes" in el:
            coords = [road_nodes[n] for n in el["nodes"] if n in road_nodes]
            if len(coords) >= 2:
                road_lines.append(LineString(coords))

    print(f"  {len(road_lines)} segmentos de estrada encontrados")

    # Buffer de ~10m (em graus: ~0.00012 a lat 41)
    roads_buffered = union_geom(road_lines).buffer(0.00012)

    def apply_roads_mask(filepath, roads_geom):
        img = Image.open(filepath).convert("RGBA")
        w, h = img.size
        arr = np.array(img)
        lon_min, lon_max = -8.70, -8.54
        lat_min, lat_max = 41.13, 41.19
        from shapely import contains_xy as _cxy

        xs = np.linspace(lon_min, lon_max, w)
        ys = np.linspace(lat_max, lat_min, h)
        xx, yy = np.meshgrid(xs, ys)
        rmask = _cxy(roads_geom, xx.ravel(), yy.ravel()).reshape(h, w)
        arr[rmask, 3] = 0
        Image.fromarray(arr).save(filepath)
        n_masked = rmask.sum()
        print(
            f"  {os.path.basename(filepath)}: {n_masked} pixels mascarados (estradas)"
        )

    apply_roads_mask(os.path.join(LAYERS_DIR, "interior_subsistente.png"), roads_buffered)
    apply_roads_mask(os.path.join(LAYERS_DIR, "interior_perdido.png"), roads_buffered)
    print("Mascara de estradas aplicada.")
else:
    print("  AVISO: Overpass indisponivel, mascara de estradas nao aplicada")

# ----- Phase 2b: Filtragem vectorial (area + linearidade) -----
print("\nA filtrar por area e forma (vectorial)...")
from scipy import ndimage

# Resolucao: graus por pixel
ref_img = Image.open(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
W, H = ref_img.size
lon_min, lon_max = -8.70, -8.54
lat_min, lat_max = 41.13, 41.19
dx_deg = (lon_max - lon_min) / W  # graus/pixel em longitude
dy_deg = (lat_max - lat_min) / H  # graus/pixel em latitude
# Conversao aproximada a metros (lat ~41.16)
import math

lat_mid = (lat_min + lat_max) / 2
m_per_deg_lat = 111320
m_per_deg_lon = 111320 * math.cos(math.radians(lat_mid))
pixel_area_m2 = (dx_deg * m_per_deg_lon) * (dy_deg * m_per_deg_lat)
print(
    f"  Resolucao: {dx_deg * m_per_deg_lon:.1f} x {dy_deg * m_per_deg_lat:.1f} m/pixel, area pixel: {pixel_area_m2:.0f} m2"
)

# Mascara VCI rasterizada para distinguir centro/periferia
from shapely import contains_xy as _contains_xy

xs_grid = np.linspace(lon_min, lon_max, W)
ys_grid = np.linspace(lat_max, lat_min, H)
xx_grid, yy_grid = np.meshgrid(xs_grid, ys_grid)
if centro_union is not None:
    vci_mask = _contains_xy(centro_union, xx_grid.ravel(), yy_grid.ravel()).reshape(
        H, W
    )
else:
    vci_mask = np.ones((H, W), dtype=bool)

MIN_AREA_CENTRO = 3000  # m2
MIN_AREA_PERIFERIA = 40000  # m2


def filter_by_vector(filepath):
    """Vectorizar pixels, filtrar por area e forma, guardar PNG limpo."""
    img = Image.open(filepath).convert("RGBA")
    arr = np.array(img)
    # Mascara binaria: pixel visivel (alpha > 0)
    visible = arr[:, :, 3] > 0

    # Etiquetar componentes conexos
    labeled, n_features = ndimage.label(visible)
    print(f"  {os.path.basename(filepath)}: {n_features} componentes encontrados")

    kept = 0
    removed_area = 0
    for label_id in range(1, n_features + 1):
        component = labeled == label_id
        n_pixels = component.sum()
        area_m2 = n_pixels * pixel_area_m2

        # Determinar se esta dentro ou fora da VCI (maioria dos pixels)
        inside_vci = vci_mask[component].sum() > n_pixels / 2
        min_area = MIN_AREA_CENTRO if inside_vci else MIN_AREA_PERIFERIA

        # Filtro de area
        if area_m2 < min_area:
            arr[component, 3] = 0
            removed_area += 1
            continue

        kept += 1

    Image.fromarray(arr).save(filepath)
    print(f"    Mantidos: {kept}, removidos por area: {removed_area}")


filter_by_vector(os.path.join(LAYERS_DIR, "interior_subsistente.png"))
filter_by_vector(os.path.join(LAYERS_DIR, "interior_perdido.png"))
print("Filtragem vectorial concluida.")

# ----- Phase 3: HTML map -----
print("\nA construir mapa...")
build_html(SCRIPT_DIR, LAYERS_DIR, BOUNDS)
