"""
Teste de classificacao 1947 — area pequena (1000m x 1000m).
Centro: 41°09'35.40"N, 8°36'54.25"W
Mapa HTML interativo com ortofoto WMS + overlays.
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

# Centro em graus decimais
CENTER_LAT = 41 + 9/60 + 35.40/3600   # 41.15983
CENTER_LON = -(8 + 36/60 + 54.25/3600) # -8.61507
HALF_M = 500

# EPSG:3857
cx = CENTER_LON * 20037508.34 / 180.0
cy_rad = math.radians(CENTER_LAT)
cy = 20037508.34 * math.log(math.tan(math.pi / 4 + cy_rad / 2)) / math.pi

BBOX_3857 = {
    'xmin': cx - HALF_M, 'ymin': cy - HALF_M,
    'xmax': cx + HALF_M, 'ymax': cy + HALF_M,
}

# Bounds em WGS84 para o Leaflet
def m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

lat_s, lon_w = m3857_to_wgs84(BBOX_3857['xmin'], BBOX_3857['ymin'])
lat_n, lon_e = m3857_to_wgs84(BBOX_3857['xmax'], BBOX_3857['ymax'])
BOUNDS = [[lat_s, lon_w], [lat_n, lon_e]]

SIZE = 2048

print(f'Centro: {CENTER_LAT:.5f}N, {CENTER_LON:.5f}W')
print(f'Resolucao: {1000/SIZE:.2f} m/pixel')

# ============================================================
# 1. Download
# ============================================================
cache = 'layers/test_1947_raw.png'
os.makedirs('layers', exist_ok=True)
if os.path.exists(cache):
    print('Imagem em cache')
    img = Image.open(cache).convert('RGB')
else:
    print('A descarregar...')
    bbox_str = f"{BBOX_3857['xmin']},{BBOX_3857['ymin']},{BBOX_3857['xmax']},{BBOX_3857['ymax']}"
    params = {
        'SERVICE': 'WMS', 'VERSION': '1.1.1', 'REQUEST': 'GetMap',
        'LAYERS': LAYER, 'SRS': 'EPSG:3857',
        'BBOX': bbox_str, 'WIDTH': SIZE, 'HEIGHT': SIZE,
        'FORMAT': 'image/png', 'TRANSPARENT': 'false',
    }
    r = requests.get(WMS_URL, params=params, timeout=60)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert('RGB')
    img.save(cache)

gray = np.mean(np.array(img)[:,:,:3], axis=2).astype(np.uint8)
print(f'Imagem: {img.size}')

# ============================================================
# 2. Features
# ============================================================
from scipy.ndimage import uniform_filter, sobel, median_filter

gray_f = gray.astype(np.float32) / 255.0
W = 15

mean = uniform_filter(gray_f, size=W)
sq_mean = uniform_filter(gray_f ** 2, size=W)
std = np.sqrt(np.clip(sq_mean - mean ** 2, 0, None))
gx = sobel(gray_f, axis=1)
gy = sobel(gray_f, axis=0)
grad = uniform_filter(np.sqrt(gx**2 + gy**2), size=W)
ent = uniform_filter(np.abs(gray_f - mean), size=max(W // 2, 5))

features = np.stack([gray_f, mean, std, grad, ent], axis=-1)

# ============================================================
# 3. Treino automatico
# ============================================================
from sklearn.ensemble import RandomForestClassifier

veg_mask = (mean < 0.40) & (std > 0.04)
built_mask = (mean > 0.55) & (std < 0.03)

np.random.seed(42)
veg_coords = np.argwhere(veg_mask)
built_coords = np.argwhere(built_mask)
n_samples = min(5000, len(veg_coords), len(built_coords))
print(f'Amostras: {n_samples} veg, {n_samples} edif')

veg_idx = np.random.choice(len(veg_coords), n_samples, replace=False)
built_idx = np.random.choice(len(built_coords), n_samples, replace=False)

X_train = np.vstack([
    features[veg_coords[veg_idx, 0], veg_coords[veg_idx, 1]],
    features[built_coords[built_idx, 0], built_coords[built_idx, 1]],
])
y_train = np.array([1] * n_samples + [2] * n_samples)

print('A treinar...')
rf = RandomForestClassifier(n_estimators=200, max_depth=15, n_jobs=-1, random_state=42)
rf.fit(X_train, y_train)

# ============================================================
# 4. Classificar
# ============================================================
print('A classificar...')
X_all = features.reshape(-1, 5)
y_pred = rf.predict(X_all).reshape(SIZE, SIZE)

no_data = (gray < 5) | (gray > 250)
y_pred[no_data] = 0
y_pred = median_filter(y_pred, size=7)
y_pred[no_data] = 0

n_veg = np.sum(y_pred == 1)
n_built = np.sum(y_pred == 2)
total = n_veg + n_built
pct_veg = n_veg / total * 100
pct_built = n_built / total * 100
print(f'Vegetacao: {pct_veg:.1f}%  |  Edificado: {pct_built:.1f}%')

# ============================================================
# 5. Exportar camadas PNG
# ============================================================
CLASSES = {1: ('Vegetacao', '#228B22'), 2: ('Edificado', '#888888')}
layer_paths = {}

for cls, (name, color_hex) in CLASSES.items():
    mask = (y_pred == cls).astype(np.uint8) * 255
    rgba = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    ch = color_hex.lstrip('#')
    r, g, b = int(ch[0:2], 16), int(ch[2:4], 16), int(ch[4:6], 16)
    rgba[mask > 0] = [r, g, b, 200]
    path = f'layers/test_1947_{name.lower()}.png'
    Image.fromarray(rgba).save(path)
    layer_paths[cls] = path
    print(f'  {name}: {os.path.getsize(path)//1024} KB')

# ============================================================
# 6. Mapa HTML
# ============================================================
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
<title>Teste classificacao 1947 (1km x 1km)</title>
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
  <b style="font-size:14px;">Teste 1947</b><br>
  <span style="color:#aaa;font-size:10px;">1km &times; 1km &bull; 0.49 m/pixel</span>

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
  <span style="color:#666;font-size:10px;">Ortofoto 1947 (CIIMAR/FCUP)</span>
</div>

<script>
var map = L.map('map').setView([{CENTER_LAT}, {CENTER_LON}], 16);
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

output = 'test_1947.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa: {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(os.path.abspath(output))
