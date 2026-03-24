"""
Classificacao do ortofotomapa 1947 — municipio do Porto.
Processamento por tiles (1km x 1km a 2048x2048 cada).
Abordagem pixel: 4 features de textura local + Random Forest.
Treino: coordenadas manuais fornecidas pelo utilizador.
Fonte WMS: CIIMAR/FCUP. Mascara municipio via GEE (CAOP2025).
"""
import ee
import requests
import numpy as np
import os
import math
import base64
import io
import json
import time
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# ============================================================
# Config
# ============================================================
WMS_URL = 'https://gis.ciimar.up.pt/porto/wms'
LAYER = 'Orto_Porto_1947'
CRS = 'EPSG:3857'

# BBOX que contem o municipio do Porto (EPSG:3857)
BBOX_3857 = {
    'xmin': -968578.0,
    'ymin': 5031536.0,
    'xmax': -950671.0,
    'ymax': 5040407.0,
}

def m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon

# Tile config: cada tile 1km x 1km a 2048x2048 (0.49 m/pixel)
TILE_SIZE_M = 1000
TILE_PX = 2048

# Mosaico final (resolucao total dos tiles)
TOTAL_W_M = BBOX_3857['xmax'] - BBOX_3857['xmin']
TOTAL_H_M = BBOX_3857['ymax'] - BBOX_3857['ymin']
N_TILES_X = math.ceil(TOTAL_W_M / TILE_SIZE_M)
N_TILES_Y = math.ceil(TOTAL_H_M / TILE_SIZE_M)
TILE_OUT = TILE_PX
MOSAIC_W = N_TILES_X * TILE_OUT
MOSAIC_H = N_TILES_Y * TILE_OUT

# BOUNDS calculados a partir da extensao real do mosaico
_mosaic_xmax = BBOX_3857['xmin'] + N_TILES_X * TILE_SIZE_M
_mosaic_ymin = BBOX_3857['ymax'] - N_TILES_Y * TILE_SIZE_M
_lat_s, _lon_w = m3857_to_wgs84(BBOX_3857['xmin'], _mosaic_ymin)
_lat_n, _lon_e = m3857_to_wgs84(_mosaic_xmax, BBOX_3857['ymax'])
BOUNDS = [[_lat_s, _lon_w], [_lat_n, _lon_e]]

CLASSES = {1: 'Vegetacao', 2: 'Edificado'}
COLORS = {1: '#228B22', 2: '#888888'}

FEATURE_NAMES = ['intensidade', 'media_local', 'std_local', 'gradiente']
FEATURE_WINDOW = 15

# Overlap entre tiles (em pixels) para evitar artefactos de fronteira.
# Os filtros (uniform_filter W=15, sobel 3x3, median 7) precisam de contexto
# nos bordos. 100px (~50m) garante features correctas nas juncoes.
OVERLAP_PX = 100

os.makedirs('layers', exist_ok=True)

# ============================================================
# Coordenadas de treino manuais (fornecidas pelo utilizador)
# ============================================================
def _dms(d, m, s):
    return d + m / 60 + s / 3600

TRAINING_SAMPLES = [
    # Vegetacao
    (1, -_dms(8, 36, 38.37), _dms(41, 9, 43.11)),
    (1, -_dms(8, 36, 43.91), _dms(41, 9, 41.49)),
    (1, -_dms(8, 36, 54.57), _dms(41, 9, 40.98)),
    (1, -_dms(8, 36, 46.04), _dms(41, 9, 39.36)),
    # Campos claros (vegetacao, nao confundir com edificado)
    (1, -_dms(8, 36, 53.44), _dms(41, 9, 45.69)),
    (1, -_dms(8, 36, 54.96), _dms(41, 9, 35.22)),
    # Edificado
    (2, -_dms(8, 36, 49.77), _dms(41, 9, 42.33)),
    (2, -_dms(8, 36, 48.76), _dms(41, 9, 31.08)),
    (2, -_dms(8, 36, 58.41), _dms(41, 9, 46.63)),
    # Edificios brancos (telhados muito claros)
    (2, -_dms(8, 37, 8.34), _dms(41, 9, 47.44)),
    (2, -_dms(8, 37, 8.76), _dms(41, 9, 48.39)),
]


# ============================================================
# 1. Mascara do municipio via GEE
# ============================================================
def get_porto_mask():
    cache_path = 'layers/porto_municipio_mask_tiles.png'
    if os.path.exists(cache_path):
        print('  Mascara em cache')
        return np.array(Image.open(cache_path).convert('L')) > 128

    print('  A obter limites do municipio via GEE...')
    porto_geom = ee.Geometry.Polygon([
        [[-8.70, 41.10], [-8.53, 41.10], [-8.53, 41.20], [-8.70, 41.20]]
    ])
    municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
    porto_muni = municipios.filterBounds(porto_geom).filter(
        ee.Filter.eq('municipio', 'Porto')
    )
    coords = porto_muni.geometry().coordinates().getInfo()

    mask_img = Image.new('L', (MOSAIC_W, MOSAIC_H), 0)
    draw = ImageDraw.Draw(mask_img)

    def lonlat_to_pixel(lon, lat):
        x = lon * 20037508.34 / 180.0
        y_rad = math.radians(lat)
        y = 20037508.34 * math.log(math.tan(math.pi / 4 + y_rad / 2)) / math.pi
        px = int((x - BBOX_3857['xmin']) / TOTAL_W_M * MOSAIC_W)
        py = int((BBOX_3857['ymax'] - y) / TOTAL_H_M * MOSAIC_H)
        return (px, py)

    for ring_group in coords:
        if isinstance(ring_group[0][0], list):
            for ring in ring_group:
                poly = [lonlat_to_pixel(c[0], c[1]) for c in ring]
                draw.polygon(poly, fill=255)
        else:
            poly = [lonlat_to_pixel(c[0], c[1]) for c in ring_group]
            draw.polygon(poly, fill=255)

    mask_img.save(cache_path)
    print(f'  Mascara: {MOSAIC_W}x{MOSAIC_H}')
    return np.array(mask_img) > 128


# ============================================================
# 2. Download de um tile WMS
# ============================================================
def _download_wms_rect(bbox_3857, width, height, cache_path=None):
    """Descarrega um rectangulo arbitrario do WMS."""
    if cache_path and os.path.exists(cache_path):
        return np.array(Image.open(cache_path).convert('L'))

    bbox_str = f"{bbox_3857[0]},{bbox_3857[1]},{bbox_3857[2]},{bbox_3857[3]}"
    params = {
        'SERVICE': 'WMS', 'VERSION': '1.1.1', 'REQUEST': 'GetMap',
        'LAYERS': LAYER, 'SRS': CRS, 'BBOX': bbox_str,
        'WIDTH': width, 'HEIGHT': height,
        'FORMAT': 'image/png', 'TRANSPARENT': 'false',
    }
    for attempt in range(5):
        try:
            r = requests.get(WMS_URL, params=params, timeout=120)
            r.raise_for_status()
            img_rgb = Image.open(io.BytesIO(r.content)).convert('RGB')
            arr = np.array(img_rgb)
            gray_arr = np.mean(arr[:, :, :3], axis=2).astype(np.uint8)
            img = Image.fromarray(gray_arr)
            if cache_path:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                img.save(cache_path)
            return np.array(img)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            wait = 5 * (attempt + 1)
            print(f'    [retry {attempt+1}/5, esperar {wait}s]', end=' ', flush=True)
            time.sleep(wait)
    raise RuntimeError(f'Falhou apos 5 tentativas')


def download_tile(tx, ty):
    """Descarrega tile sem overlap (para treino)."""
    cache_path = f'layers/tiles_1947/tile_{ty}_{tx}.png'
    x0 = BBOX_3857['xmin'] + tx * TILE_SIZE_M
    y0 = BBOX_3857['ymax'] - (ty + 1) * TILE_SIZE_M
    return _download_wms_rect(
        (x0, y0, x0 + TILE_SIZE_M, y0 + TILE_SIZE_M),
        TILE_PX, TILE_PX, cache_path
    )


def download_tile_with_overlap(tx, ty):
    """Descarrega tile com margem extra (OVERLAP_PX) para classificacao."""
    overlap_m = OVERLAP_PX * (TILE_SIZE_M / TILE_PX)  # pixels -> metros
    x0 = BBOX_3857['xmin'] + tx * TILE_SIZE_M - overlap_m
    y0 = BBOX_3857['ymax'] - (ty + 1) * TILE_SIZE_M - overlap_m
    x1 = x0 + TILE_SIZE_M + 2 * overlap_m
    y1 = y0 + TILE_SIZE_M + 2 * overlap_m
    size_px = TILE_PX + 2 * OVERLAP_PX
    # Sem cache — o overlap varia conforme a posicao
    return _download_wms_rect((x0, y0, x1, y1), size_px, size_px)


# ============================================================
# 3. Extrair features pixel (igual ao teste)
# ============================================================
def extract_features(gray):
    from scipy.ndimage import uniform_filter, sobel
    gray_f = gray.astype(np.float32) / 255.0
    W = FEATURE_WINDOW
    mean = uniform_filter(gray_f, size=W)
    sq_mean = uniform_filter(gray_f ** 2, size=W)
    std = np.sqrt(np.clip(sq_mean - mean ** 2, 0, None))
    gx = sobel(gray_f, axis=1)
    gy = sobel(gray_f, axis=0)
    grad = np.sqrt(gx**2 + gy**2)
    grad_smooth = uniform_filter(grad, size=W)
    return np.stack([gray_f, mean, std, grad_smooth], axis=-1)


# ============================================================
# 4. Treino: extrair pixels das coordenadas manuais
# ============================================================
def geo_to_tile_and_pixel(lon, lat):
    x = lon * 20037508.34 / 180.0
    y_rad = math.radians(lat)
    y = 20037508.34 * math.log(math.tan(math.pi / 4 + y_rad / 2)) / math.pi
    frac_x = (x - BBOX_3857['xmin']) / TILE_SIZE_M
    frac_y = (BBOX_3857['ymax'] - y) / TILE_SIZE_M
    tx = int(frac_x)
    ty = int(frac_y)
    lx = int((frac_x - tx) * TILE_PX)
    ly = int((frac_y - ty) * TILE_PX)
    return tx, ty, lx, ly


def collect_training():
    """Descarrega tiles de treino, extrai features, recolhe pixels."""
    from scipy.ndimage import median_filter

    # Descobrir que tiles contem pontos de treino
    needed_tiles = {}
    for cls, lon, lat in TRAINING_SAMPLES:
        tx, ty, lx, ly = geo_to_tile_and_pixel(lon, lat)
        key = (ty, tx)
        if key not in needed_tiles:
            needed_tiles[key] = []
        needed_tiles[key].append((cls, lx, ly))

    print(f'  {len(needed_tiles)} tile(s) de treino')

    RADIUS = 10  # ~5m a volta de cada ponto
    X_train = []
    y_train = []

    for (ty, tx), points in needed_tiles.items():
        gray = download_tile(tx, ty)
        feat = extract_features(gray)

        for cls, lx, ly in points:
            for dy in range(-RADIUS, RADIUS + 1):
                for dx in range(-RADIUS, RADIUS + 1):
                    ny, nx = ly + dy, lx + dx
                    if 0 <= ny < TILE_PX and 0 <= nx < TILE_PX:
                        X_train.append(feat[ny, nx])
                        y_train.append(cls)

    X_train = np.array(X_train)
    y_train = np.array(y_train)
    n_veg = np.sum(y_train == 1)
    n_edif = np.sum(y_train == 2)
    print(f'  {n_veg} pixels vegetacao, {n_edif} pixels edificado')
    return X_train, y_train


def train_rf(X_train, y_train):
    from sklearn.ensemble import RandomForestClassifier

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_leaf=5,
        n_jobs=-1, random_state=42, class_weight='balanced',
    )
    rf.fit(X_train, y_train)

    print('  Importancia:')
    for name, imp in sorted(zip(FEATURE_NAMES, rf.feature_importances_), key=lambda x: -x[1]):
        print(f'    {name:16s}: {imp:.3f}')

    return rf


# ============================================================
# 5. Classificar todos os tiles e montar mosaico
# ============================================================
def classify_mosaic(rf, muni_mask):
    from scipy.ndimage import median_filter

    classified = np.zeros((MOSAIC_H, MOSAIC_W), dtype=np.uint8)
    processed = 0
    OV = OVERLAP_PX

    for ty in range(N_TILES_Y):
        for tx in range(N_TILES_X):
            # Verificar se o tile tem municipio
            y0 = ty * TILE_OUT
            x0 = tx * TILE_OUT
            y1 = min(y0 + TILE_OUT, MOSAIC_H)
            x1 = min(x0 + TILE_OUT, MOSAIC_W)
            tile_mask_out = muni_mask[y0:y1, x0:x1]

            muni_frac = np.mean(tile_mask_out) if tile_mask_out.size > 0 else 0
            if muni_frac < 0.05:
                continue

            t0 = time.time()
            print(f'  Tile ({ty},{tx}): {muni_frac*100:.0f}% municipio...', end=' ', flush=True)

            # Descarregar com overlap para features correctas nos bordos
            gray_full = download_tile_with_overlap(tx, ty)
            full_size = TILE_PX + 2 * OV

            # Mascara do tile a resolucao TILE_PX
            tile_mask = np.array(
                Image.fromarray(tile_mask_out.astype(np.uint8) * 255)
                .resize((TILE_PX, TILE_PX), Image.NEAREST)
            ) > 128

            # Verificar se ha dados (na regiao central, sem overlap)
            gray_center = gray_full[OV:OV+TILE_PX, OV:OV+TILE_PX]
            valid_px = np.sum((gray_center > 5) & (gray_center < 250) & tile_mask)
            if valid_px < 1000:
                print('sem dados, a saltar')
                continue

            # Extrair features sobre a imagem COMPLETA (com overlap)
            feat_full = extract_features(gray_full)

            # Classificar a imagem completa
            X_all = feat_full.reshape(-1, len(FEATURE_NAMES))
            y_pred_full = rf.predict(X_all).reshape(full_size, full_size)

            # Mascarar nodata na imagem completa e filtro mediano
            nodata_full = (gray_full < 5) | (gray_full > 250)
            y_pred_full[nodata_full] = 0
            y_pred_full = median_filter(y_pred_full, size=7)
            y_pred_full[nodata_full] = 0

            # Recortar a regiao central (sem overlap)
            y_pred = y_pred_full[OV:OV+TILE_PX, OV:OV+TILE_PX]

            # Mascarar fora do municipio
            y_pred[~tile_mask] = 0

            # Colocar no mosaico (resolucao total, sem downsampling)
            th = y1 - y0
            tw = x1 - x0
            classified[y0:y1, x0:x1] = y_pred[:th, :tw].astype(np.uint8)
            processed += 1
            print(f'{time.time()-t0:.0f}s')

    # Mascara final do municipio
    classified[~muni_mask] = 0
    print(f'\n  {processed} tiles processados')
    return classified


# ============================================================
# 6. Estatisticas
# ============================================================
def compute_stats(classified, muni_mask):
    total_valid = np.sum(classified > 0)
    area_porto_km2 = 41.42

    print('\n  === Uso do solo Porto 1947 ===')
    coverage = total_valid / np.sum(muni_mask) * 100 if np.sum(muni_mask) > 0 else 0
    print(f'  Cobertura: {coverage:.1f}%')

    results = {}
    for cls in sorted(CLASSES.keys()):
        n = np.sum(classified == cls)
        pct = n / total_valid * 100 if total_valid > 0 else 0
        area = pct / 100 * area_porto_km2
        print(f'    {CLASSES[cls]:20s}: {pct:5.1f}% ({area:.2f} km2)')
        results[cls] = {'pct': pct, 'area_km2': area}

    return results


# ============================================================
# 7. Exportar camadas
# ============================================================
def export_layers(classified):
    h, w = classified.shape
    # Reduzir para export (HTML viavel) — metade da resolucao total
    export_h, export_w = h // 2, w // 2
    classified_small = np.array(
        Image.fromarray(classified).resize((export_w, export_h), Image.NEAREST)
    )
    print(f'  Export: {export_w}x{export_h} ({w}x{h} full res)')
    paths = {}

    for cls in sorted(CLASSES.keys()):
        mask = (classified_small == cls).astype(np.uint8) * 255
        rgba = np.zeros((export_h, export_w, 4), dtype=np.uint8)
        color_hex = COLORS[cls].lstrip('#')
        r, g, b = int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16)
        rgba[mask > 0] = [r, g, b, 200]

        filename = f'uso_1947_{CLASSES[cls].lower()}.png'
        filepath = f'layers/{filename}'
        Image.fromarray(rgba).save(filepath, optimize=True)
        print(f'  {filename} ({os.path.getsize(filepath)//1024} KB)')
        paths[cls] = filepath

    return paths


# ============================================================
# 8. Mapa HTML
# ============================================================
def build_html(layer_paths, stats):
    def to_base64(filepath):
        with open(filepath, 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

    layers_data = []
    for cls in sorted(CLASSES.keys()):
        pct = stats[cls]['pct']
        layers_data.append({
            'id': f'uso_1947_{cls}',
            'label': f'{CLASSES[cls]} ({pct:.1f}%)',
            'color': COLORS[cls],
            'show': True,
            'src': to_base64(layer_paths[cls]),
        })

    layers_js = ',\n'.join(
        f'{{id:"{l["id"]}",label:"{l["label"]}",color:"{l["color"]}",'
        f'show:{str(l["show"]).lower()},src:"{l["src"]}"}}'
        for l in layers_data
    )

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
<title>Uso do solo Porto 1947</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); min-width:280px;
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
  <b style="font-size:14px;">Porto 1947</b><br>
  <span style="color:#aaa;font-size:10px;">Ortofotomapa a&eacute;reo &bull; Pixel RF &bull; CIIMAR/FCUP</span>

  <div class="section">Uso do solo (1947)</div>
  <div id="landuse-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <div style="margin-top:8px;">
    <label style="font-size:11px;color:#aaa;">Opacidade classificacao:</label><br>
    <input type="range" id="opacity-slider" min="0" max="100" value="70"
           style="width:100%;margin-top:4px;">
  </div>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">
    Fonte: Ortofotomapa 1947 (CIIMAR/FCUP)<br>
    Classificacao: Pixel RF (4 features textura local)<br>
    Limites: CAOP 2025 (DGT)
  </span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var bounds = {json.dumps(BOUNDS)};

var basemapConfigs = {json.dumps([[name, url] for name, url in basemaps])};
var baseTile = null;
var wmsLayer = null;

function setBasemap(idx) {{
  if (baseTile) {{ map.removeLayer(baseTile); baseTile = null; }}
  if (wmsLayer) {{ map.removeLayer(wmsLayer); wmsLayer = null; }}
  var name = basemapConfigs[idx][0];
  var url = basemapConfigs[idx][1];
  if (name === 'Ortofoto 1947') {{
    wmsLayer = L.tileLayer.wms('{WMS_URL}', {{
      layers: '{LAYER}', format: 'image/png', transparent: false,
      version: '1.1.1', maxZoom: 20, attribution: 'CIIMAR/FCUP'
    }}).addTo(map);
  }} else {{
    baseTile = L.tileLayer(url, {{maxZoom:19, attribution:''}}).addTo(map);
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
    overlays.push({{overlay: ov, mask: m, color: L_.color, visible: L_.show}});

    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      overlays[idx].visible = this.checked;
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
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';
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

    output = 'orto_1947.html'
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nMapa: {output} ({os.path.getsize(output)//1024} KB)')
    return output


# ============================================================
# Main
# ============================================================
if __name__ == '__main__':
    print(f'=== Pixel RF Porto 1947 (tiles {TILE_SIZE_M}m, {TILE_PX}px) ===')
    print(f'    Grid: {N_TILES_X} x {N_TILES_Y} tiles, mosaico {MOSAIC_W}x{MOSAIC_H}\n')

    print('1. Mascara do municipio...')
    muni_mask = get_porto_mask()

    print('\n2. Treino (coordenadas manuais)...')
    X_train, y_train = collect_training()
    rf = train_rf(X_train, y_train)

    print('\n3. Classificar mosaico...')
    classified = classify_mosaic(rf, muni_mask)

    print('\n4. Estatisticas...')
    stats = compute_stats(classified, muni_mask)

    print('\n5. Exportar camadas...')
    layer_paths = export_layers(classified)

    print('\n6. Mapa HTML...')
    html_path = build_html(layer_paths, stats)

    import webbrowser
    webbrowser.open(html_path)
    print('\nConcluido!')
