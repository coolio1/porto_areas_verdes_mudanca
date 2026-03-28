import ee
import requests
import os
import base64
import io
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]
DIM = 2048

municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(porto).filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(BANDS))
    def process(img):
        scl = img.select('SCL')
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi = img.normalizedDifference(['B11', 'B8']).rename('ndbi')
        nir_green = img.select('B8').divide(img.select('B3').max(1)).rename('nir_green')
        green = img.select('B3').rename('green')
        return ndvi.addBands(ndbi).addBands(nir_green).addBands(green).updateMask(clear)
    return s2.map(process)

def getComposite(years):
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])
    for year in years:
        full = getS2col(f'{year}-05-01', f'{year}-10-31')
        all_col = all_col.merge(full)
        spring = getS2col(f'{year}-05-15', f'{year}-06-30')
        spring_col = spring_col.merge(spring)
    median = all_col.median().clip(porto)
    spring_ndvi = spring_col.select('ndvi').reduce(
        ee.Reducer.percentile([15])).rename('spring_ndvi').clip(porto)
    ndvi_min = all_col.select('ndvi').reduce(
        ee.Reducer.percentile([10])).rename('ndvi_min').clip(porto)
    return median.addBands(spring_ndvi).addBands(ndvi_min)

print('A calcular compositos Sentinel-2...')
s2_early = getComposite([2016, 2017])
s2_late  = getComposite([2024, 2025])

# ESA WorldCover 10m (2021) como desempate
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(porto)
esaBuilt = esa.eq(50)

def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min):
    b3_ok = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isTreeStrict = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok))
    b3_ok_mixed = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTreeStrict.Not()))
    isTree = isTreeStrict.Or(isMixed)
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isBuilt, isSolo

ndvi_e = s2_early.select('ndvi')
ndbi_e = s2_early.select('ndbi')
nirgreen_e = s2_early.select('nir_green')
green_e = s2_early.select('green')
spring_ndvi_e = s2_early.select('spring_ndvi')
ndvi_min_e = s2_early.select('ndvi_min')

ndvi_l = s2_late.select('ndvi')
ndbi_l = s2_late.select('ndbi')
nirgreen_l = s2_late.select('nir_green')
green_l = s2_late.select('green')
spring_ndvi_l = s2_late.select('spring_ndvi')
ndvi_min_l = s2_late.select('ndvi_min')

isTree_e, isBuilt_e, isSolo_e = classify(ndvi_e, ndbi_e, nirgreen_e, green_e, spring_ndvi_e, ndvi_min_e)
isTree_l_base, isBuilt_l_base, _ = classify(ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l)

# Persistence rule: built in 2016 stays built unless NDVI 2025 >= 0.45
stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isSolo_l = isTree_l.Not().And(isBuilt_l.Not())

# Neighbourhood filter: fraction of built pixels within 50m radius
print('A calcular filtro de vizinhanca...')
built_fraction = isBuilt_l.unmask(0).reduceNeighborhood(
    reducer=ee.Reducer.mean(),
    kernel=ee.Kernel.circle(radius=50, units='meters')
)
is_interior = built_fraction.gte(0.6)

# Subsistente: green/soil in 2024 AND surrounded by buildings
isGreen_l = isTree_l.Or(isSolo_l)
subsistente = isGreen_l.And(is_interior).selfMask()

# Perdido: was green/soil in 2016, now built in 2024, AND surrounded by buildings
isGreen_e = isTree_e.Or(isSolo_e)
perdido = isGreen_e.And(isBuilt_l).And(is_interior).selfMask()

print('Classificacao e filtro de vizinhanca concluidos.')

from PIL import Image
import time

os.makedirs('layers', exist_ok=True)

def download_layer(image, color_hex, filename):
    filepath = f'layers/{filename}'
    if os.path.exists(filepath):
        print(f'  {filename} ja existe, a saltar...')
        return filepath
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    for attempt in range(3):
        url = vis.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
        print(f'  A descarregar {filename}...')
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert('RGBA')
            break
        except Exception as e:
            print(f'  Tentativa {attempt+1} falhou: {e}')
            if attempt < 2:
                time.sleep(3)
            else:
                return None
    pixels = list(img.getdata())
    new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
    img.putdata(new_data)
    img.save(filepath)
    print(f'  {filename} guardado ({os.path.getsize(filepath)//1024} KB)')
    return filepath

print('\nA descarregar camadas...')
download_layer(subsistente, '2E7D32', 'interior_subsistente.png')
download_layer(perdido, 'D7263D', 'interior_perdido.png')

# Municipios (reuse if exists)
muni_styled = ee.Image().paint(municipiosPorto, 0, 2).selfMask()
download_layer(muni_styled, 'FFFFFF', 'municipios.png')

from shapely.geometry import shape, box, MultiPolygon
from shapely.ops import unary_union
import numpy as np

# ----- Phase 2: OSM park mask -----
print('\nA descarregar espacos verdes publicos do OSM...')

OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
OVERPASS_QUERY = """
[out:json][timeout:60];
(
  way["leisure"="park"](41.13,-8.70,41.19,-8.54);
  relation["leisure"="park"](41.13,-8.70,41.19,-8.54);
  way["leisure"="garden"](41.13,-8.70,41.19,-8.54);
  relation["leisure"="garden"](41.13,-8.70,41.19,-8.54);
  way["landuse"="recreation_ground"](41.13,-8.70,41.19,-8.54);
  relation["landuse"="recreation_ground"](41.13,-8.70,41.19,-8.54);
);
out body;
>;
out skel qt;
"""

resp = requests.get(OVERPASS_URL, params={'data': OVERPASS_QUERY})
osm_data = resp.json()

# Build node lookup
nodes = {}
for el in osm_data['elements']:
    if el['type'] == 'node':
        nodes[el['id']] = (el['lon'], el['lat'])

# Build polygons from ways
park_polys = []
for el in osm_data['elements']:
    if el['type'] == 'way' and 'nodes' in el:
        coords = [nodes[n] for n in el['nodes'] if n in nodes]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            from shapely.geometry import Polygon as ShapelyPolygon
            park_polys.append(ShapelyPolygon(coords))

# Build polygons from relations (multipolygons)
for el in osm_data['elements']:
    if el['type'] == 'relation' and el.get('tags', {}).get('type') == 'multipolygon':
        outers = []
        for member in el.get('members', []):
            if member['type'] == 'way' and member['role'] == 'outer':
                for w in osm_data['elements']:
                    if w['type'] == 'way' and w['id'] == member['ref']:
                        coords = [nodes[n] for n in w['nodes'] if n in nodes]
                        if len(coords) >= 4 and coords[0] == coords[-1]:
                            from shapely.geometry import Polygon as ShapelyPolygon
                            outers.append(ShapelyPolygon(coords))
        park_polys.extend(outers)

if park_polys:
    parks_union = unary_union(park_polys)
    print(f'  {len(park_polys)} poligonos de parques/jardins encontrados')
else:
    parks_union = MultiPolygon()
    print('  Nenhum parque encontrado (mascara OSM nao aplicada)')

def apply_osm_mask(filepath, parks_geom):
    if parks_geom.is_empty:
        return
    img = Image.open(filepath).convert('RGBA')
    w, h = img.size
    arr = np.array(img)

    lon_min, lon_max = -8.70, -8.54
    lat_min, lat_max = 41.13, 41.19

    from shapely.vectorized import contains
    xs = np.linspace(lon_min, lon_max, w)
    ys = np.linspace(lat_max, lat_min, h)
    xx, yy = np.meshgrid(xs, ys)
    mask = contains(parks_geom, xx, yy)

    arr[mask, 3] = 0
    Image.fromarray(arr).save(filepath)
    n_masked = mask.sum()
    print(f'  {os.path.basename(filepath)}: {n_masked} pixels mascarados (parques)')

apply_osm_mask('layers/interior_subsistente.png', parks_union)
apply_osm_mask('layers/interior_perdido.png', parks_union)
print('Mascara OSM aplicada.')