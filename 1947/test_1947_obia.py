"""
Classificacao OBIA do ortofotomapa 1947 — area de teste (1000m x 1000m).
Centro: 41°09'35.40"N, 8°36'54.25"W
Segmentacao SLIC + features por objecto + Random Forest.
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
CENTER_LAT = 41 + 9/60 + 35.40/3600
CENTER_LON = -(8 + 36/60 + 54.25/3600)
HALF_M = 500

# EPSG:3857
cx = CENTER_LON * 20037508.34 / 180.0
cy_rad = math.radians(CENTER_LAT)
cy = 20037508.34 * math.log(math.tan(math.pi / 4 + cy_rad / 2)) / math.pi

BBOX_3857 = {
    'xmin': cx - HALF_M, 'ymin': cy - HALF_M,
    'xmax': cx + HALF_M, 'ymax': cy + HALF_M,
}

def m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

lat_s, lon_w = m3857_to_wgs84(BBOX_3857['xmin'], BBOX_3857['ymin'])
lat_n, lon_e = m3857_to_wgs84(BBOX_3857['xmax'], BBOX_3857['ymax'])
BOUNDS = [[lat_s, lon_w], [lat_n, lon_e]]

SIZE = 2048

CLASSES = {1: ('Vegetacao', '#228B22'), 2: ('Edificado', '#888888')}

os.makedirs('layers', exist_ok=True)

# ============================================================
# 1. Download
# ============================================================
cache = 'layers/test_1947_raw.png'
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

gray = np.mean(np.array(img)[:, :, :3], axis=2).astype(np.uint8)
gray_f = gray.astype(np.float32) / 255.0
print(f'Imagem: {gray.shape}, {1000/SIZE:.2f} m/pixel')

# ============================================================
# 2. Segmentacao SLIC
# ============================================================
from skimage.segmentation import slic
from skimage.measure import regionprops
from skimage.feature import graycomatrix, graycoprops
from scipy.ndimage import sobel, binary_dilation

print('\nA segmentar (SLIC)...')
segments = slic(gray_f, n_segments=4000, compactness=10, sigma=1.5,
                channel_axis=None, start_label=0)
n_segs = segments.max() + 1
print(f'  {n_segs} segmentos')

# ============================================================
# 3. Features por objecto
# ============================================================
print('A extrair features...')

# Pre-computar gradiente
gx = sobel(gray_f, axis=1)
gy = sobel(gray_f, axis=0)
gradient = np.sqrt(gx**2 + gy**2)

FEATURE_NAMES = [
    'media', 'std', 'mediana', 'amplitude', 'grad_medio',
    'dens_bordas', 'entropia', 'glcm_contraste', 'glcm_homog',
    'compacidade', 'elongacao', 'log_area', 'contraste_fronteira',
    'grad_std',          # variancia do gradiente interno
    'nitidez_contorno',  # gradiente nos pixels de fronteira do segmento
]

feature_matrix = np.zeros((n_segs, 15))
props = regionprops(segments + 1, intensity_image=gray)

for prop in props:
    idx = prop.label - 1
    mask = segments == idx
    intensities = gray_f[mask]
    grad_vals = gradient[mask]

    # Intensidade
    feature_matrix[idx, 0] = np.mean(intensities)
    feature_matrix[idx, 1] = np.std(intensities)
    feature_matrix[idx, 2] = np.median(intensities)
    feature_matrix[idx, 3] = np.ptp(intensities)

    # Gradiente
    feature_matrix[idx, 4] = np.mean(grad_vals)
    feature_matrix[idx, 5] = np.mean(grad_vals > 0.05)

    # Entropia
    hist, _ = np.histogram(intensities, bins=32, range=(0, 1))
    hist = hist / (hist.sum() + 1e-10)
    hist = hist[hist > 0]
    feature_matrix[idx, 6] = -np.sum(hist * np.log2(hist))

    # GLCM (no bounding box do segmento)
    min_r, min_c, max_r, max_c = prop.bbox
    sub = gray[min_r:max_r, min_c:max_c]
    if sub.shape[0] > 3 and sub.shape[1] > 3:
        sub_q = (sub // 16).astype(np.uint8)
        try:
            glcm = graycomatrix(sub_q, distances=[1], angles=[0, np.pi/4],
                                levels=16, symmetric=True, normed=True)
            feature_matrix[idx, 7] = graycoprops(glcm, 'contrast').mean()
            feature_matrix[idx, 8] = graycoprops(glcm, 'homogeneity').mean()
        except Exception:
            pass

    # Variancia do gradiente (edificios: bordas definidas nos contornos, interior liso)
    feature_matrix[idx, 13] = np.std(grad_vals) if len(grad_vals) > 1 else 0

    # Forma
    perim = prop.perimeter if prop.perimeter > 0 else 1
    feature_matrix[idx, 9] = 4 * np.pi * prop.area / (perim ** 2)
    minor = prop.minor_axis_length if prop.minor_axis_length > 0 else 1
    feature_matrix[idx, 10] = prop.major_axis_length / minor
    feature_matrix[idx, 11] = np.log(prop.area + 1)

# Contraste fronteira + nitidez de contorno
from skimage.segmentation import find_boundaries

print('  Contraste fronteira + nitidez contorno...')
boundary_map = find_boundaries(segments, mode='inner')

for idx in range(n_segs):
    mask = segments == idx
    dilated = binary_dilation(mask, iterations=2)
    neighbor_mask = dilated & ~mask
    if neighbor_mask.any():
        own_mean = np.mean(gray_f[mask])
        neighbor_mean = np.mean(gray_f[neighbor_mask])
        feature_matrix[idx, 12] = abs(own_mean - neighbor_mean)

    # Nitidez de contorno: gradiente medio nos pixels de fronteira do segmento
    border_pixels = mask & boundary_map
    if border_pixels.any():
        feature_matrix[idx, 14] = np.mean(gradient[border_pixels])

print(f'  {len(FEATURE_NAMES)} features extraidas')

# ============================================================
# 4. Treino supervisionado com amostras manuais
# ============================================================
from sklearn.ensemble import RandomForestClassifier

def dms_to_dd(d, m, s):
    return d + m / 60 + s / 3600

def geo_to_pixel_local(lon, lat):
    """Converte lon,lat (WGS84) para pixel na imagem de teste."""
    x = lon * 20037508.34 / 180.0
    y_rad = math.radians(lat)
    y = 20037508.34 * math.log(math.tan(math.pi / 4 + y_rad / 2)) / math.pi
    px = int((x - BBOX_3857['xmin']) / (BBOX_3857['xmax'] - BBOX_3857['xmin']) * SIZE)
    py = int((BBOX_3857['ymax'] - y) / (BBOX_3857['ymax'] - BBOX_3857['ymin']) * SIZE)
    return px, py

# Amostras manuais fornecidas pelo utilizador
TRAINING_COORDS = [
    # Vegetacao
    (1, -dms_to_dd(8, 36, 38.37), dms_to_dd(41, 9, 43.11)),
    (1, -dms_to_dd(8, 36, 43.91), dms_to_dd(41, 9, 41.49)),
    (1, -dms_to_dd(8, 36, 54.57), dms_to_dd(41, 9, 40.98)),
    (1, -dms_to_dd(8, 36, 46.04), dms_to_dd(41, 9, 39.36)),
    # Campos claros (nao confundir com edificado)
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

# Mapear cada coordenada para o segmento correspondente + vizinhos
train_seg_ids = {}  # seg_id -> class
for cls, lon, lat in TRAINING_COORDS:
    px, py = geo_to_pixel_local(lon, lat)
    # Apanhar segmentos num raio de 30px (~15m) à volta do ponto
    for dy in range(-30, 31, 10):
        for dx in range(-30, 31, 10):
            ny, nx = py + dy, px + dx
            if 0 <= ny < SIZE and 0 <= nx < SIZE:
                seg_id = segments[ny, nx]
                if seg_id not in train_seg_ids:
                    train_seg_ids[seg_id] = cls

n_veg = sum(1 for v in train_seg_ids.values() if v == 1)
n_built = sum(1 for v in train_seg_ids.values() if v == 2)
print(f'\nTreino supervisionado: {n_veg} seg vegetacao, {n_built} seg edificado')

seg_ids = list(train_seg_ids.keys())
X_train = feature_matrix[seg_ids]
y_train = np.array([train_seg_ids[s] for s in seg_ids])

print('A treinar Random Forest...')
rf = RandomForestClassifier(
    n_estimators=300, max_depth=12, min_samples_leaf=3,
    n_jobs=-1, random_state=42, class_weight='balanced',
)
rf.fit(X_train, y_train)

print('Importancia:')
for name, imp in sorted(zip(FEATURE_NAMES, rf.feature_importances_), key=lambda x: -x[1]):
    print(f'  {name:22s}: {imp:.3f}')

# ============================================================
# 5. Classificar todos os segmentos
# ============================================================
print('\nA classificar...')
y_pred_segs = rf.predict(feature_matrix)

# Mapear de volta para pixels
classified = np.zeros((SIZE, SIZE), dtype=np.uint8)
for seg_id in range(n_segs):
    classified[segments == seg_id] = y_pred_segs[seg_id]

# Mascarar sem dados
no_data = (gray < 5) | (gray > 250)
classified[no_data] = 0

n_veg = np.sum(classified == 1)
n_built = np.sum(classified == 2)
total = n_veg + n_built
pct_veg = n_veg / total * 100
pct_built = n_built / total * 100
print(f'Vegetacao: {pct_veg:.1f}%  |  Edificado: {pct_built:.1f}%')

# ============================================================
# 6. Exportar PNGs
# ============================================================
print('\nA exportar...')
layer_paths = {}
for cls, (name, color_hex) in CLASSES.items():
    mask = (classified == cls).astype(np.uint8) * 255
    rgba = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    ch = color_hex.lstrip('#')
    r, g, b = int(ch[0:2], 16), int(ch[2:4], 16), int(ch[4:6], 16)
    rgba[mask > 0] = [r, g, b, 200]
    path = f'layers/test_1947_obia_{name.lower()}.png'
    Image.fromarray(rgba).save(path)
    layer_paths[cls] = path
    print(f'  {name}: {os.path.getsize(path)//1024} KB')

# ============================================================
# 7. Mapa HTML
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
<title>OBIA teste 1947 (1km x 1km)</title>
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
  <b style="font-size:14px;">OBIA teste 1947</b><br>
  <span style="color:#aaa;font-size:10px;">1km &times; 1km &bull; 0.49 m/pixel &bull; {n_segs} segmentos</span>

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
  <span style="color:#666;font-size:10px;">OBIA: SLIC + Random Forest<br>Ortofoto 1947 (CIIMAR/FCUP)</span>
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

output = 'test_1947_obia.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Mapa: {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(os.path.abspath(output))
print('Concluido!')
