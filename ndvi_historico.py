"""
NDVI historico do Porto (1985-2024) usando Landsat 5/8/9.
Compara vegetacao ao longo de ~40 anos com NDVI medio de verao.
"""
import ee
import requests
import os
import base64
import io
import time

ee.Initialize(project='REDACTED')

# Mesma area do projecto original
porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

# Municipios para fronteiras
municipios = ee.FeatureCollection('projects/REDACTED/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

# ============================================================
# Epocas: janelas de 5-6 anos para maximizar cenas disponiveis
# ============================================================
EPOCHS = [
    ('1985-90',  'Landsat 5',  [1985, 1986, 1987, 1988, 1989, 1990]),
    ('1995-00',  'Landsat 5',  [1995, 1996, 1997, 1998, 1999, 2000]),
    ('2001-05',  'Landsat 5',  [2001, 2002, 2003, 2004, 2005]),
    ('2016-17',  'Landsat 8',  [2016, 2017]),
    ('2023-24',  'Landsat 8',  [2023, 2024]),
]

# ============================================================
# Funcoes de processamento Landsat
# ============================================================

def cloud_mask_l5(img):
    """Cloud mask para Landsat 5 TM Collection 2 Level 2."""
    qa = img.select('QA_PIXEL')
    cloud = qa.bitwiseAnd(1 << 3).eq(0)       # bit 3 = cloud
    shadow = qa.bitwiseAnd(1 << 4).eq(0)       # bit 4 = cloud shadow
    return img.updateMask(cloud).updateMask(shadow)

def cloud_mask_l8(img):
    """Cloud mask para Landsat 8/9 OLI Collection 2 Level 2."""
    qa = img.select('QA_PIXEL')
    cloud = qa.bitwiseAnd(1 << 3).eq(0)
    shadow = qa.bitwiseAnd(1 << 4).eq(0)
    return img.updateMask(cloud).updateMask(shadow)

def ndvi_l5(img):
    """NDVI para Landsat 5 TM (SR_B4=NIR, SR_B3=Red)."""
    img = cloud_mask_l5(img)
    nir = img.select('SR_B4').multiply(0.0000275).add(-0.2)
    red = img.select('SR_B3').multiply(0.0000275).add(-0.2)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
    return ndvi.clamp(-1, 1)

def ndvi_l8(img):
    """NDVI para Landsat 8/9 OLI (SR_B5=NIR, SR_B4=Red)."""
    img = cloud_mask_l8(img)
    nir = img.select('SR_B5').multiply(0.0000275).add(-0.2)
    red = img.select('SR_B4').multiply(0.0000275).add(-0.2)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
    return ndvi.clamp(-1, 1)

def get_ndvi_composite(sensor, years):
    """Composito NDVI mediana de verao (Jun-Set) para varios anos."""
    cols = []
    for year in years:
        start = f'{year}-06-01'
        end = f'{year}-09-30'
        if sensor == 'Landsat 5':
            col = (ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
                .filterBounds(porto)
                .filterDate(start, end)
                .filter(ee.Filter.lt('CLOUD_COVER', 40))
                .map(ndvi_l5))
        else:  # Landsat 8/9
            col8 = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                .filterBounds(porto)
                .filterDate(start, end)
                .filter(ee.Filter.lt('CLOUD_COVER', 40))
                .map(ndvi_l8))
            col9 = (ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
                .filterBounds(porto)
                .filterDate(start, end)
                .filter(ee.Filter.lt('CLOUD_COVER', 40))
                .map(ndvi_l8))
            col = col8.merge(col9)
        cols.append(col)

    merged = cols[0]
    for c in cols[1:]:
        merged = merged.merge(c)

    count = merged.size()
    median = merged.median().clip(porto)
    return median, count

# ============================================================
# Calcular compositos
# ============================================================
print('A calcular compositos NDVI por epoca...')
composites = {}
for name, sensor, years in EPOCHS:
    ndvi, count = get_ndvi_composite(sensor, years)
    n = count.getInfo()
    print(f'  {name} ({sensor}): {n} cenas')
    composites[name] = ndvi

# ============================================================
# Download das camadas
# ============================================================
os.makedirs('layers_historico', exist_ok=True)
DIM = 2048

# Paleta NDVI: castanho -> amarelo -> verde escuro
NDVI_PALETTE = ['8B4513', 'D2B48C', 'F5DEB3', 'FFFF00', 'ADFF2F', '32CD32', '228B22', '006400']

def download_ndvi(image, filename, label):
    """Download NDVI como PNG colorido."""
    from PIL import Image as PILImage

    filepath = f'layers_historico/{filename}'
    if os.path.exists(filepath):
        print(f'  {filename} ja existe, a saltar...')
        return filepath

    vis = image.visualize(min=0, max=0.8, palette=NDVI_PALETTE)
    for attempt in range(3):
        url = vis.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
        print(f'  A descarregar {label}...')
        r = requests.get(url)
        try:
            img = PILImage.open(io.BytesIO(r.content)).convert('RGBA')
            break
        except Exception as e:
            print(f'  Tentativa {attempt+1} falhou: {e}')
            if attempt < 2:
                time.sleep(3)
            else:
                print(f'  ERRO: nao foi possivel descarregar {filename}')
                return None

    img.save(filepath)
    print(f'  {filename} guardado ({os.path.getsize(filepath)//1024} KB)')
    return filepath

def download_diff(image, filename, label):
    """Download camada de diferenca NDVI como PNG colorido."""
    from PIL import Image as PILImage

    filepath = f'layers_historico/{filename}'
    if os.path.exists(filepath):
        print(f'  {filename} ja existe, a saltar...')
        return filepath

    diff_palette = ['d73027', 'f46d43', 'fdae61', 'ffffbf', 'a6d96a', '1a9850', '006837']
    vis = image.visualize(min=-0.3, max=0.3, palette=diff_palette)
    for attempt in range(3):
        url = vis.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
        print(f'  A descarregar {label}...')
        r = requests.get(url)
        try:
            img = PILImage.open(io.BytesIO(r.content)).convert('RGBA')
            break
        except Exception as e:
            print(f'  Tentativa {attempt+1} falhou: {e}')
            if attempt < 2:
                time.sleep(3)
            else:
                return None

    img.save(filepath)
    print(f'  {filename} guardado ({os.path.getsize(filepath)//1024} KB)')
    return filepath

def download_mask(image, color_hex, filename):
    """Download mascara binaria como PNG."""
    from PIL import Image as PILImage

    filepath = f'layers_historico/{filename}'
    if os.path.exists(filepath):
        print(f'  {filename} ja existe, a saltar...')
        return filepath

    vis = image.visualize(palette=[color_hex], min=0, max=1)
    for attempt in range(3):
        url = vis.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
        print(f'  A descarregar {filename}...')
        r = requests.get(url)
        try:
            img = PILImage.open(io.BytesIO(r.content)).convert('RGBA')
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

# Download NDVI por epoca
print('\nA descarregar camadas NDVI...')
for name, sensor, years in EPOCHS:
    download_ndvi(composites[name], f'ndvi_{name}.png', f'NDVI {name}')

# Diferencas chave
print('\nA calcular diferencas...')
diff_layers = [
    ('diff_85_24', composites['2023-24'].subtract(composites['1985-90']),
     'Mudanca 1985-90 vs 2023-24'),
    ('diff_95_24', composites['2023-24'].subtract(composites['1995-00']),
     'Mudanca 1995-00 vs 2023-24'),
    ('diff_05_24', composites['2023-24'].subtract(composites['2001-05']),
     'Mudanca 2001-05 vs 2023-24'),
]

for did, diff_img, label in diff_layers:
    download_diff(diff_img, f'{did}.png', label)

# Municipios
print('\nA descarregar limites...')
muni_styled = ee.Image().paint(municipiosPorto, 0, 2).selfMask()
download_mask(muni_styled, 'FFFFFF', 'municipios.png')

# ============================================================
# Estatisticas NDVI por epoca
# ============================================================
print('\n--- Estatisticas NDVI medio por epoca ---')
for name, sensor, years in EPOCHS:
    stats = composites[name].reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=porto,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    ndvi_mean = stats.get('ndvi', 'N/A')
    if isinstance(ndvi_mean, (int, float)):
        print(f'  {name}: NDVI medio = {ndvi_mean:.4f}')
    else:
        print(f'  {name}: NDVI medio = {ndvi_mean}')

# ============================================================
# Construir mapa HTML
# ============================================================
print('\nA construir mapa HTML...')

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

# Layers para o mapa
NDVI_LAYERS = []
for name, sensor, years in EPOCHS:
    yr_range = f'{years[0]}-{years[-1]}'
    NDVI_LAYERS.append((f'ndvi_{name}', f'NDVI {yr_range} ({sensor})', True))

DIFF_LAYERS_INFO = [
    ('diff_85_24', 'Mudanca 1985-90 \u2192 2023-24', False),
    ('diff_95_24', 'Mudanca 1995-00 \u2192 2023-24', False),
    ('diff_05_24', 'Mudanca 2001-05 \u2192 2023-24', False),
]

ALL_MAP_LAYERS = NDVI_LAYERS + DIFF_LAYERS_INFO + [('municipios', 'Limites municipais', True)]

layers_js_items = []
for lid, label, show in ALL_MAP_LAYERS:
    b64 = to_base64(f'layers_historico/{lid}.png')
    layers_js_items.append(
        '{' + f'id:"{lid}",label:"{label}",show:{str(show).lower()},src:"{b64}"' + '}'
    )
layers_js = ',\n'.join(layers_js_items)

n_ndvi = len(NDVI_LAYERS)
n_diff = len(DIFF_LAYERS_INFO)

basemaps = [
    ('CartoDB Dark', 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'),
    ('Satelite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'),
    ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
]
basemap_options = ''.join(
    f'<option value="{url}"{"selected" if i==0 else ""}>{name}</option>'
    for i, (name, url) in enumerate(basemaps)
)

html = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>NDVI historico do Porto (1985-2024)</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body { margin:0; }
  #map { position:absolute; top:0; bottom:0; width:100%; }
  #panel {
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); min-width:300px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }
  .row { display:flex; align-items:center; gap:6px; margin:2px 0; }
  .row input[type=checkbox] { width:15px; height:15px; cursor:pointer; margin:0; }
  .row label { cursor:pointer; font-size:12px; }
  .section { font-size:11px; color:#aaa; font-weight:bold; margin:8px 0 4px 0; }
  select { background:#333; color:#eee; border:1px solid #555; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }
  .legend {
    margin:8px 0; padding:6px 8px; background:rgba(50,50,50,0.8); border-radius:6px;
  }
  .legend-bar {
    height:12px; border-radius:3px; margin:4px 0;
  }
  .legend-labels { display:flex; justify-content:space-between; font-size:10px; color:#bbb; }
  .radio-group { margin:6px 0; }
  .radio-group label { display:block; cursor:pointer; padding:2px 0; font-size:12px; }
  .radio-group input { margin-right:6px; }
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">NDVI historico do Porto</b><br>
  <span style="color:#aaa;font-size:10px;">1985-2024 &bull; Landsat 30m</span>

  <div class="section">NDVI por epoca (selecionar uma)</div>
  <div id="ndvi-radios" class="radio-group"></div>

  <div class="legend">
    <div style="font-size:10px;color:#aaa;margin-bottom:2px;">NDVI (vegetacao)</div>
    <div class="legend-bar" style="background:linear-gradient(to right, #8B4513, #D2B48C, #F5DEB3, #FFFF00, #ADFF2F, #32CD32, #228B22, #006400);"></div>
    <div class="legend-labels"><span>0 (solo)</span><span>0.4</span><span>0.8 (denso)</span></div>
  </div>

  <div class="section">Mudancas de NDVI</div>
  <div id="diff-rows"></div>

  <div class="legend" id="diff-legend" style="display:none;">
    <div style="font-size:10px;color:#aaa;margin-bottom:2px;">Diferenca NDVI</div>
    <div class="legend-bar" style="background:linear-gradient(to right, #d73027, #f46d43, #fdae61, #ffffbf, #a6d96a, #1a9850, #006837);"></div>
    <div class="legend-labels"><span>-0.3 (perda)</span><span>0</span><span>+0.3 (ganho)</span></div>
  </div>

  <div class="section">Outros</div>
  <div id="other-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">''' + basemap_options + '''</select>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">Fonte: Landsat (USGS/NASA) &bull; 30m resolucao</span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer("''' + basemaps[0][1] + '''", {maxZoom:19, attribution:''}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {maxZoom:19, attribution:''}).addTo(map);
});

var bounds = ''' + str(BOUNDS) + ''';
var layers = [''' + layers_js + '''];
var overlays = [];
var nNdvi = ''' + str(n_ndvi) + ''';
var nDiff = ''' + str(n_diff) + ''';

async function init() {
  for (var i = 0; i < layers.length; i++) {
    var ov = L.imageOverlay(layers[i].src, bounds);
    overlays.push(ov);
  }

  var divRadios = document.getElementById('ndvi-radios');
  for (var i = 0; i < nNdvi; i++) {
    var lbl = document.createElement('label');
    var rb = document.createElement('input');
    rb.type = 'radio'; rb.name = 'ndvi_epoch'; rb.value = i;
    if (i === nNdvi - 1) { rb.checked = true; overlays[i].addTo(map); }
    rb.addEventListener('change', function() {
      var sel = +this.value;
      for (var j = 0; j < nNdvi; j++) {
        if (j === sel) overlays[j].addTo(map);
        else map.removeLayer(overlays[j]);
      }
    });
    lbl.appendChild(rb);
    lbl.appendChild(document.createTextNode(' ' + layers[i].label));
    divRadios.appendChild(lbl);
  }

  var divDiff = document.getElementById('diff-rows');
  var diffLegend = document.getElementById('diff-legend');
  for (var i = nNdvi; i < nNdvi + nDiff; i++) {
    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = false; cb.dataset.idx = i;
    cb.addEventListener('change', function() {
      var idx = +this.dataset.idx;
      if (this.checked) overlays[idx].addTo(map);
      else map.removeLayer(overlays[idx]);
      var anyDiff = false;
      for (var j = nNdvi; j < nNdvi + nDiff; j++) {
        if (map.hasLayer(overlays[j])) anyDiff = true;
      }
      diffLegend.style.display = anyDiff ? 'block' : 'none';
    });
    var lb = document.createElement('label');
    lb.textContent = layers[i].label;
    row.appendChild(cb);
    row.appendChild(lb);
    divDiff.appendChild(row);
  }

  var divOther = document.getElementById('other-rows');
  for (var i = nNdvi + nDiff; i < layers.length; i++) {
    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = layers[i].show; cb.dataset.idx = i;
    if (layers[i].show) overlays[i].addTo(map);
    cb.addEventListener('change', function() {
      var idx = +this.dataset.idx;
      if (this.checked) overlays[idx].addTo(map);
      else map.removeLayer(overlays[idx]);
    });
    var lb = document.createElement('label');
    lb.textContent = layers[i].label;
    row.appendChild(cb);
    row.appendChild(lb);
    divOther.appendChild(row);
  }
}

init();
</script>
</body>
</html>'''

output = 'ndvi_historico.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)
