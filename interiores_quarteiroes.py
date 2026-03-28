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

# Neighbourhood filter: pixels verdes com edificado na vizinhanca (borda de interiores)
print('A calcular filtro de vizinhanca...')
isGreen_l = isTree_l.Or(isSolo_l)
isGreen_e = isTree_e.Or(isSolo_e)

built_fraction = isBuilt_l.unmask(0).reduceNeighborhood(
    reducer=ee.Reducer.mean(),
    kernel=ee.Kernel.circle(radius=50, units='meters')
)
is_edge_interior = built_fraction.gte(0.5)

# Flood-fill: crescer das bordas para dentro, preenchendo interiores grandes
# Sementes = pixels verdes na borda (junto a edificios)
print('A preencher interiores (flood-fill)...')
interior_fill = isGreen_l.And(is_edge_interior)
for _ in range(10):  # ~100m de crescimento (10 iter x 10m/pixel)
    grown = interior_fill.focal_max(radius=10, units='meters')
    interior_fill = grown.And(isGreen_l).Or(interior_fill)

# Subsistente: green/soil em 2024 dentro de interiores de quarteirão
subsistente_raw = isGreen_l.And(interior_fill).selfMask()

# Perdido: era green/soil em 2016, agora edificado, na zona de interiores
# Usar o mesmo flood-fill mas para a epoca 2016
interior_fill_e = isGreen_e.And(is_edge_interior)
for _ in range(10):
    grown = interior_fill_e.focal_max(radius=10, units='meters')
    interior_fill_e = grown.And(isGreen_e).Or(interior_fill_e)
perdido_raw = isGreen_e.And(isBuilt_l).And(interior_fill_e).selfMask()

# Filtro de area minima: remover manchas com menos de 30 pixels conexos (~3000 m2)
MIN_PIXELS = 30
subsistente_count = subsistente_raw.connectedPixelCount(MIN_PIXELS + 1)
subsistente = subsistente_raw.updateMask(subsistente_count.gte(MIN_PIXELS))

perdido_count = perdido_raw.connectedPixelCount(MIN_PIXELS + 1)
perdido = perdido_raw.updateMask(perdido_count.gte(MIN_PIXELS))

print('Classificacao e filtro de vizinhanca concluidos.')

from PIL import Image
import numpy as np
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
    arr = np.array(img)
    dark = (arr[:,:,0] < 10) & (arr[:,:,1] < 10) & (arr[:,:,2] < 10)
    arr[dark, 3] = 0
    img = Image.fromarray(arr)
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

# ----- Phase 2: OSM park mask -----
print('\nA descarregar espacos verdes publicos do OSM...')

OVERPASS_URLS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
]
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

osm_data = None
for overpass_url in OVERPASS_URLS:
    for attempt in range(3):
        print(f'  A tentar {overpass_url} (tentativa {attempt+1})...')
        resp = requests.get(overpass_url, params={'data': OVERPASS_QUERY}, timeout=90)
        if resp.status_code == 200:
            try:
                osm_data = resp.json()
                break
            except Exception:
                pass
        time.sleep(5)
    if osm_data:
        break

if not osm_data:
    print('  AVISO: Overpass API indisponivel, mascara OSM nao aplicada')
    osm_data = {'elements': []}

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

    from shapely import contains_xy
    xs = np.linspace(lon_min, lon_max, w)
    ys = np.linspace(lat_max, lat_min, h)
    xx, yy = np.meshgrid(xs, ys)
    mask = contains_xy(parks_geom, xx.ravel(), yy.ravel()).reshape(h, w)

    arr[mask, 3] = 0
    Image.fromarray(arr).save(filepath)
    n_masked = mask.sum()
    print(f'  {os.path.basename(filepath)}: {n_masked} pixels mascarados (parques)')

apply_osm_mask('layers/interior_subsistente.png', parks_union)
apply_osm_mask('layers/interior_perdido.png', parks_union)
print('Mascara OSM aplicada.')

# ----- Phase 3: HTML map -----
print('\nA construir mapa...')

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

MAP_LAYERS = [
    ('interior_subsistente', 'Subsistente', '#2E7D32', True),
    ('interior_perdido', 'Perdido', '#D7263D', True),
    ('municipios', 'Limites municipais', '#FFFFFF', True),
]

layers_js_items = []
for lid, label, color, show in MAP_LAYERS:
    b64 = to_base64(f'layers/{lid}.png')
    layers_js_items.append(
        f'{{id:"{lid}",label:"{label}",color:"{color}",show:{str(show).lower()},src:"{b64}"}}'
    )
layers_js = ',\n'.join(layers_js_items)

basemaps = [
    ('CartoDB Positron', 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'),
    ('CartoDB Dark', 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'),
    ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
    ('Satelite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'),
]
basemap_options = ''.join(
    f'<option value="{url}"{"selected" if i==0 else ""}>{name}</option>'
    for i, (name, url) in enumerate(basemaps)
)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Interiores de Quarteirao - Porto</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:260px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }}
  .row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; margin:0; }}
  .row label {{ cursor:pointer; }}
  .swatch {{ width:14px; height:14px; border-radius:3px; display:inline-block; }}
  .section {{ font-size:11px; color:#888; font-weight:bold; margin:8px 0 4px 0; }}
  select {{ background:#f5f5f5; color:#222; border:1px solid #ccc; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Interiores de Quarteir&atilde;o</b><br>
  <span style="color:#888;font-size:10px;">Espa&ccedil;os verdes privados encravados no tecido urbano</span>

  <div class="section">Camadas</div>
  <div id="layer-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#ddd;margin:10px 0 4px 0;">
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; 2016-17 vs 2024-25<br>Parques exclu&iacute;dos via OpenStreetMap</span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:''}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:''}}).addTo(map);
}});

var bounds = {BOUNDS};
var layers = [{layers_js}];
var state = [];

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
  var div = document.getElementById('layer-rows');
  for (var i = 0; i < layers.length; i++) {{
    var L_ = layers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    state.push({{overlay: ov, mask: m, color: L_.color}});

    var row = document.createElement('div');
    row.className = 'row';

    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) state[idx].overlay.addTo(map);
      else map.removeLayer(state[idx].overlay);
    }});

    var sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.backgroundColor = L_.color;

    var lb = document.createElement('label');
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';

    row.appendChild(cb);
    row.appendChild(sw);
    row.appendChild(lb);
    div.appendChild(row);
  }}
}}

init();
</script>
</body>
</html>'''

output = 'interiores_quarteiroes.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)