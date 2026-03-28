"""
Classificacao do ortofotomapa 1947 — area de teste 2 (2000m x 2000m).
Centro: 41°10'37.06"N, 8°36'10.77"W (2000m x 2000m)
Treino: coordenadas manuais da area 1 (fornecidas pelo utilizador).
Abordagem pixel com features de textura local.
"""
import requests
import numpy as np
import math
import os
import io
import base64
import json
from PIL import Image

WMS_URL = 'https://gis.ciimar.up.pt/porto/wms'
LAYER = 'Orto_Porto_1947'
SIZE = 4096
HALF_M = 1000

# ============================================================
# Funcoes auxiliares
# ============================================================
def dms_to_dd(d, m, s):
    return d + m / 60 + s / 3600

def to_epsg3857(lat, lon):
    cx = lon * 20037508.34 / 180.0
    cy_rad = math.radians(lat)
    cy = 20037508.34 * math.log(math.tan(math.pi / 4 + cy_rad / 2)) / math.pi
    return cx, cy

def m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

def make_bbox(lat, lon, half_m):
    cx, cy = to_epsg3857(lat, lon)
    return {
        'xmin': cx - half_m, 'ymin': cy - half_m,
        'xmax': cx + half_m, 'ymax': cy + half_m,
    }

def geo_to_pixel(lon, lat, bbox, size):
    x, y = to_epsg3857(lat, lon)
    px = int((x - bbox['xmin']) / (bbox['xmax'] - bbox['xmin']) * size)
    py = int((bbox['ymax'] - y) / (bbox['ymax'] - bbox['ymin']) * size)
    return px, py

def download_wms(bbox, cache_path, size=SIZE):
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    if os.path.exists(cache_path):
        print(f'  Cache: {cache_path}')
        return Image.open(cache_path).convert('RGB')
    print(f'  A descarregar...')
    bbox_str = f"{bbox['xmin']},{bbox['ymin']},{bbox['xmax']},{bbox['ymax']}"
    params = {
        'SERVICE': 'WMS', 'VERSION': '1.1.1', 'REQUEST': 'GetMap',
        'LAYERS': LAYER, 'SRS': 'EPSG:3857',
        'BBOX': bbox_str, 'WIDTH': size, 'HEIGHT': size,
        'FORMAT': 'image/png', 'TRANSPARENT': 'false',
    }
    r = requests.get(WMS_URL, params=params, timeout=60)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert('RGB')
    img.save(cache_path)
    return img

def extract_features(gray_f, W=15):
    """Features pixel: intensidade + textura local (media, std, gradiente)."""
    from scipy.ndimage import uniform_filter, sobel
    mean = uniform_filter(gray_f, size=W)
    sq_mean = uniform_filter(gray_f ** 2, size=W)
    std = np.sqrt(np.clip(sq_mean - mean ** 2, 0, None))
    gx = sobel(gray_f, axis=1)
    gy = sobel(gray_f, axis=0)
    grad = np.sqrt(gx**2 + gy**2)
    grad_smooth = uniform_filter(grad, size=W)
    return np.stack([gray_f, mean, std, grad_smooth], axis=-1)

# ============================================================
# Area 1 (treino) — centro: 41°09'35.40"N, 8°36'54.25"W (1000m)
# ============================================================
A1_LAT = dms_to_dd(41, 9, 35.40)
A1_LON = -dms_to_dd(8, 36, 54.25)
A1_HALF_M = 500
A1_SIZE = 2048
A1_BBOX = make_bbox(A1_LAT, A1_LON, A1_HALF_M)

# Area 2 (classificar) — centro: 41°10'37.06"N, 8°36'10.77"W
A2_LAT = dms_to_dd(41, 10, 37.06)
A2_LON = -dms_to_dd(8, 36, 10.77)
A2_BBOX = make_bbox(A2_LAT, A2_LON, HALF_M)

# Bounds WGS84 para Leaflet (area 2)
lat_s, lon_w = m3857_to_wgs84(A2_BBOX['xmin'], A2_BBOX['ymin'])
lat_n, lon_e = m3857_to_wgs84(A2_BBOX['xmax'], A2_BBOX['ymax'])
BOUNDS = [[lat_s, lon_w], [lat_n, lon_e]]

# ============================================================
# Coordenadas de treino manuais (fornecidas pelo utilizador, area 1)
# ============================================================
TRAINING_COORDS = [
    # Vegetacao
    (1, -dms_to_dd(8, 36, 38.37), dms_to_dd(41, 9, 43.11)),
    (1, -dms_to_dd(8, 36, 43.91), dms_to_dd(41, 9, 41.49)),
    (1, -dms_to_dd(8, 36, 54.57), dms_to_dd(41, 9, 40.98)),
    (1, -dms_to_dd(8, 36, 46.04), dms_to_dd(41, 9, 39.36)),
    # Campos claros (vegetacao, nao confundir com edificado)
    (1, -dms_to_dd(8, 36, 53.44), dms_to_dd(41, 9, 45.69)),
    (1, -dms_to_dd(8, 36, 54.96), dms_to_dd(41, 9, 35.22)),
    # Edificado
    (2, -dms_to_dd(8, 36, 49.77), dms_to_dd(41, 9, 42.33)),
    (2, -dms_to_dd(8, 36, 48.76), dms_to_dd(41, 9, 31.08)),
    (2, -dms_to_dd(8, 36, 58.41), dms_to_dd(41, 9, 46.63)),
    # Edificios brancos (telhados muito claros)
    (2, -dms_to_dd(8, 37, 8.34), dms_to_dd(41, 9, 47.44)),
    (2, -dms_to_dd(8, 37, 8.76), dms_to_dd(41, 9, 48.39)),
]

# ============================================================
# 1. Descarregar ambas as areas
# ============================================================
print('=== Area 1 (treino) ===')
img1 = download_wms(A1_BBOX, 'layers/test_1947_raw.png', size=A1_SIZE)
gray1 = np.mean(np.array(img1)[:, :, :3], axis=2).astype(np.uint8)
gray1_f = gray1.astype(np.float32) / 255.0

print('=== Area 2 (classificar) ===')
img2 = download_wms(A2_BBOX, 'layers/test_1947_area2_raw.png')
gray2 = np.mean(np.array(img2)[:, :, :3], axis=2).astype(np.uint8)
gray2_f = gray2.astype(np.float32) / 255.0

print(f'Resolucao: {1000/SIZE:.2f} m/pixel')

# ============================================================
# 2. Extrair features
# ============================================================
print('\nA extrair features...')
feat1 = extract_features(gray1_f)
feat2 = extract_features(gray2_f)
n_feat = feat1.shape[-1]
print(f'  {n_feat} features: intensidade, media local, std local, gradiente')

# ============================================================
# 3. Amostras de treino (da area 1)
# ============================================================
from sklearn.ensemble import RandomForestClassifier
from scipy.ndimage import median_filter

RADIUS = 10  # pixels (~5m) a volta de cada ponto

X_train_list = []
y_train_list = []

for cls, lon, lat in TRAINING_COORDS:
    px, py = geo_to_pixel(lon, lat, A1_BBOX, A1_SIZE)
    # Extrair janela de pixels a volta do ponto
    for dy in range(-RADIUS, RADIUS + 1):
        for dx in range(-RADIUS, RADIUS + 1):
            ny, nx = py + dy, px + dx
            if 0 <= ny < A1_SIZE and 0 <= nx < A1_SIZE:
                X_train_list.append(feat1[ny, nx])
                y_train_list.append(cls)

X_train = np.array(X_train_list)
y_train = np.array(y_train_list)

n_veg_t = np.sum(y_train == 1)
n_edif_t = np.sum(y_train == 2)
print(f'\nTreino: {n_veg_t} pixels vegetacao, {n_edif_t} pixels edificado')

# ============================================================
# 4. Treinar e classificar area 2
# ============================================================
print('A treinar Random Forest...')
rf = RandomForestClassifier(
    n_estimators=200, max_depth=15, min_samples_leaf=5,
    n_jobs=-1, random_state=42, class_weight='balanced',
)
rf.fit(X_train, y_train)

feature_names = ['intensidade', 'media_local', 'std_local', 'gradiente']
print('Importancia:')
for name, imp in sorted(zip(feature_names, rf.feature_importances_), key=lambda x: -x[1]):
    print(f'  {name:16s}: {imp:.3f}')

print('\nA classificar area 2...')
X_all = feat2.reshape(-1, n_feat)
y_pred = rf.predict(X_all).reshape(SIZE, SIZE)

# Mascarar sem-dados e filtro mediano
no_data = (gray2 < 5) | (gray2 > 250)
y_pred[no_data] = 0
y_pred = median_filter(y_pred, size=7)
y_pred[no_data] = 0

n_veg = np.sum(y_pred == 1)
n_built = np.sum(y_pred == 2)
total = n_veg + n_built
pct_veg = n_veg / total * 100 if total > 0 else 0
pct_built = n_built / total * 100 if total > 0 else 0
print(f'Vegetacao: {pct_veg:.1f}%  |  Edificado: {pct_built:.1f}%')

# ============================================================
# 5. Exportar PNGs
# ============================================================
CLASSES = {1: ('Vegetacao', '#228B22'), 2: ('Edificado', '#888888')}
layer_paths = {}

for cls, (name, color_hex) in CLASSES.items():
    mask = (y_pred == cls).astype(np.uint8) * 255
    rgba = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    ch = color_hex.lstrip('#')
    r, g, b = int(ch[0:2], 16), int(ch[2:4], 16), int(ch[4:6], 16)
    rgba[mask > 0] = [r, g, b, 200]
    path = f'layers/test_1947_area2_{name.lower()}.png'
    Image.fromarray(rgba).save(path)
    layer_paths[cls] = path
    print(f'  {name}: {os.path.getsize(path)//1024} KB')

# ============================================================
# 6. Mapa HTML
# ============================================================
print('\nA construir mapa...')

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

layers_js_items = []
for cls, (name, color_hex) in CLASSES.items():
    pct = pct_veg if cls == 1 else pct_built
    b64 = to_base64(layer_paths[cls])
    layers_js_items.append(
        f'{{id:"uso_{cls}",label:"{name} ({pct:.1f}%)",color:"{color_hex}",show:true,src:"{b64}"}}'
    )
layers_js = ',\n'.join(layers_js_items)

basemaps = [
    ('Ortofoto 1947', ''),
    ('CartoDB Dark', 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'),
    ('Satelite (atual)', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'),
    ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
]
basemap_options = ''.join(
    f'<option value="{i}"{" selected" if i==0 else ""}>{name}</option>'
    for i, (name, url) in enumerate(basemaps)
)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Teste area 2 — 1947 (2km x 2km)</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); min-width:260px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }}
  .row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .row input[type=color] {{ width:22px; height:22px; border:none; cursor:pointer; padding:0; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; margin:0; }}
  .row label {{ cursor:pointer; }}
  .section {{ font-size:11px; color:#aaa; font-weight:bold; margin:8px 0 4px 0; }}
  select {{ background:#333; color:#eee; border:1px solid #555; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Teste area 2 — 1947</b><br>
  <span style="color:#aaa;font-size:10px;">2km &times; 2km &bull; 0.49 m/pixel &bull; treino da area 1</span>

  <div class="section">Uso do solo</div>
  <div id="landuse-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <div style="margin-top:8px;">
    <label style="font-size:11px;color:#aaa;">Opacidade:</label><br>
    <input type="range" id="opacity-slider" min="0" max="100" value="70"
           style="width:100%;margin-top:4px;">
  </div>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">Pixel RF (treino area 1)<br>Ortofoto 1947 (CIIMAR/FCUP)</span>
</div>

<script>
var map = L.map('map').setView([{A2_LAT}, {A2_LON}], 16);
var bounds = {json.dumps(BOUNDS)};

var basemapConfigs = {json.dumps([[n, u] for n, u in basemaps])};
var baseTile = null, wmsLayer = null;

function setBasemap(idx) {{
  if (baseTile) {{ map.removeLayer(baseTile); baseTile = null; }}
  if (wmsLayer) {{ map.removeLayer(wmsLayer); wmsLayer = null; }}
  if (basemapConfigs[idx][0] === 'Ortofoto 1947') {{
    wmsLayer = L.tileLayer.wms('{WMS_URL}', {{
      layers: '{LAYER}', format: 'image/png', transparent: false,
      version: '1.1.1', maxZoom: 22, attribution: 'CIIMAR/FCUP'
    }}).addTo(map);
  }} else {{
    baseTile = L.tileLayer(basemapConfigs[idx][1], {{maxZoom:22, attribution:''}}).addTo(map);
  }}
}}
setBasemap(0);

document.getElementById('basemap-select').addEventListener('change', function() {{
  setBasemap(parseInt(this.value));
}});

var layers = [{layers_js}];
var overlays = [];

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

function renderColored(m, hex, opacity) {{
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = m.w; c.height = m.h;
  var x = c.getContext('2d');
  var d = x.createImageData(m.w, m.h);
  var aScale = (opacity || 100) / 100;
  for (var i = 0; i < m.alpha.length; i++) {{
    d.data[i*4] = rgb[0]; d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2]; d.data[i*4+3] = Math.round(m.alpha[i] * aScale);
  }}
  x.putImageData(d, 0, 0);
  return c.toDataURL();
}}

async function init() {{
  var div = document.getElementById('landuse-rows');
  for (var i = 0; i < layers.length; i++) {{
    var L_ = layers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color, 70);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    overlays.push({{overlay: ov, mask: m, color: L_.color}});

    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) overlays[idx].overlay.addTo(map);
      else map.removeLayer(overlays[idx].overlay);
    }});
    var cp = document.createElement('input');
    cp.type = 'color'; cp.value = L_.color; cp.dataset.idx = i;
    cp.addEventListener('input', function() {{
      var idx = +this.dataset.idx;
      var s = overlays[idx];
      s.color = this.value;
      var op = document.getElementById('opacity-slider').value;
      s.overlay.setUrl(renderColored(s.mask, this.value, op));
    }});
    var lb = document.createElement('label');
    lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(cp); row.appendChild(lb);
    div.appendChild(row);
  }}

  document.getElementById('opacity-slider').addEventListener('input', function() {{
    var op = parseInt(this.value);
    for (var i = 0; i < overlays.length; i++) {{
      var s = overlays[i];
      s.overlay.setUrl(renderColored(s.mask, s.color, op));
    }}
  }});
}}
init();
</script>
</body>
</html>'''

output = 'test_1947_area2.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Mapa: {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(os.path.abspath(output))
print('Concluido!')
