"""Teste de deteccao de mudanca via embeddings AlphaEarth (Serralves).

Replica a tecnica do sample Google ADK earth-engine-geospatial:
angulo entre embeddings AlphaEarth de anos consecutivos, thresholded.
Calibracao numa area pequena antes de decidir se compensa aplicar ao municipio.
"""
import ee
import os
import io
import math
import base64
import webbrowser
import requests
from PIL import Image as PILImage
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Mesma area de teste de test_area.py (Serralves)
LAT, LON = 41.188117, -8.617633
BUFFER = 1500  # meters

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

coords = area.coordinates().getInfo()[0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BOUNDS = [[min(lats), min(lons)], [max(lats), max(lons)]]

print('A testar deteccao de mudanca por embeddings AlphaEarth...')
print(f'  Area: {BUFFER}m em redor de {LAT}N, {abs(LON)}W')
print(f'  Bounds: {BOUNDS}')

# ============================================================
# Embeddings AlphaEarth (GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL)
# Replica a logica de earth-engine-geospatial/earth_engine_geospatial/tools.py
# ============================================================
EMBEDDINGS = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')

def year_embedding(year):
    """Mosaic do embedding anual, recortado a area de teste."""
    return (EMBEDDINGS
        .filterBounds(area)
        .filter(ee.Filter.calendarRange(year, year, 'year'))
        .mosaic()
        .clip(area))

def get_angle(img1, img2):
    """Angulo entre dois embeddings (assume-os ja normalizados, tal como o sample original)."""
    return img1.multiply(img2).reduce(ee.Reducer.sum()).acos().rename('angle')

# --- Verificacao rapida: confirmar que o dataset responde para a area de teste ---
print('\nA verificar acesso ao dataset de embeddings...')
img_2020 = year_embedding(2020)
band_names = img_2020.bandNames().getInfo()
print(f'  Bandas do embedding 2020: {len(band_names)} bandas ({band_names[0]}...{band_names[-1]})')
n_images_2020 = (EMBEDDINGS.filterBounds(area)
    .filter(ee.Filter.calendarRange(2020, 2020, 'year')).size().getInfo())
print(f'  Imagens 2020 cobrindo a area de teste: {n_images_2020}')

# ============================================================
# Contagem de mudancas 2018-2025 (8 comparacoes ano-a-ano)
# ============================================================
def get_change_count_image(threshold):
    """Numero de anos (2018-2025) em que o pixel mudou significativamente.

    Compara cada ano ao anterior (2017 e o baseline do primeiro par).
    Retorna imagem de banda unica 'count', valores 0-8.
    """
    count = ee.Image.constant(0).rename('count')
    for year in range(2018, 2026):
        prev = year_embedding(year - 1)
        cur = year_embedding(year)
        changed = get_angle(prev, cur).gt(threshold).rename('count')
        count = count.add(changed)
    return count.clip(area).rename('count')

# --- Validacao numerica antes de gerar visuais (threshold default pi/4) ---
print('\nA validar contagem de mudancas (threshold pi/4, area de teste)...')
default_count = get_change_count_image(math.pi / 4)
stats = default_count.reduceRegion(
    reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
    geometry=area, scale=10, maxPixels=1e8
).getInfo()
print(f'  Media de mudancas/pixel: {stats.get("count_mean"):.2f}')
print(f'  Maximo de mudancas/pixel: {stats.get("count_max")}')

# ============================================================
# Thumbnails: contagem de mudancas visualizada, 3 thresholds
# ============================================================
# Paleta sequencial branco -> vermelho escuro, 9 niveis (contagem 0 a 8)
PALETTE = ['ffffff', 'ffe0b2', 'ffcc80', 'ffab91', 'ff8a65',
           'ff7043', 'f4511e', 'd84315', '7f0000']
DIM = 1024

THRESHOLDS = [
    ('pi6', math.pi / 6, 'Threshold pi/6 (mais sensivel)'),
    ('pi4', math.pi / 4, 'Threshold pi/4 (default do sample)'),
    ('pi3', math.pi / 3, 'Threshold pi/3 (mais conservador)'),
]

def download_change_layer(threshold, label):
    """Descarrega a contagem de mudancas visualizada (paleta 0-8) como PNG."""
    img = get_change_count_image(threshold)
    vis = img.visualize(min=0, max=8, palette=PALETTE)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar mudanca_{label}...')
    r = requests.get(url)
    r.raise_for_status()
    os.makedirs('layers/test', exist_ok=True)
    filepath = f'layers/test/mudanca_{label}.png'
    with open(filepath, 'wb') as f:
        f.write(r.content)
    return filepath

print('\nA descarregar camadas de contagem de mudancas (3 thresholds)...')
layer_paths = {}
for label, threshold, _desc in THRESHOLDS:
    layer_paths[label] = download_change_layer(threshold, label)
print(f'  Ficheiros gerados: {list(layer_paths.values())}')

# ============================================================
# HTML standalone de inspeccao (Leaflet, sem nav — nao e pagina do site)
# ============================================================
def to_b64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()

test_layers = [
    (label, desc, label == 'pi4', to_b64(layer_paths[label]))
    for label, _threshold, desc in THRESHOLDS
]

layer_js = ',\n'.join([
    f'  {{id:"{lid}", label:"{desc}", show:{str(show).lower()}, '
    f'src:"data:image/png;base64,{b64}"}}'
    for lid, desc, show, b64 in test_layers
])

center_lat = (BOUNDS[0][0] + BOUNDS[1][0]) / 2
center_lon = (BOUNDS[0][1] + BOUNDS[1][1]) / 2

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Teste mudanca embeddings AlphaEarth - Serralves</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }} #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{ position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',sans-serif; color:#eee; line-height:2.0; max-width:320px; }}
  .row {{ display:flex; align-items:center; gap:8px; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; }}
  .row input[type=range] {{ width:70px; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b>Teste: mudanca via embeddings AlphaEarth</b><br>
  <span style="color:#aaa;font-size:10px;">Contagem de mudancas 2018-2025 (0-8) | Serralves 1500m</span>
  <div id="rows"></div>
</div>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], 15);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  maxZoom:19, attribution:'Esri'
}}).addTo(map);
var bounds = {BOUNDS};
var layers = [{layer_js}];
var state = [];
function init(){{
  var div = document.getElementById('rows');
  for (var i = 0; i < layers.length; i++) {{
    var L_ = layers[i];
    var ov = L.imageOverlay(L_.src, bounds, {{opacity: 0.75}});
    if (L_.show) ov.addTo(map);
    state.push({{overlay: ov}});
    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function(){{
      var idx = +this.dataset.idx;
      if (this.checked) state[idx].overlay.addTo(map); else map.removeLayer(state[idx].overlay);
    }});
    var lb = document.createElement('label'); lb.textContent = L_.label;
    row.appendChild(cb); row.appendChild(lb); div.appendChild(row);
  }}
}}
init();
</script>
</body>
</html>'''

with open('mudanca_embeddings_teste.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('\nmudanca_embeddings_teste.html gerado')

webbrowser.open('mudanca_embeddings_teste.html')
