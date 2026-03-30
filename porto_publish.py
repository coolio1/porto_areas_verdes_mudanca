import ee
import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
    """Retorna colecao processada (sem reduzir)."""
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
    """Composito multi-sazonal: mediana verao + NDVI primavera + NDVI min."""
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

print('A calcular compositos Sentinel-2 (multi-sazonal)...')
s2_early = getComposite([2016, 2017])
s2_late  = getComposite([2024, 2025])

ndvi_e = s2_early.select('ndvi')
ndvi_l = s2_late.select('ndvi')
ndbi_e = s2_early.select('ndbi')
ndbi_l = s2_late.select('ndbi')
nirgreen_e = s2_early.select('nir_green')
nirgreen_l = s2_late.select('nir_green')
green_e = s2_early.select('green')
green_l = s2_late.select('green')
spring_ndvi_e = s2_early.select('spring_ndvi')
spring_ndvi_l = s2_late.select('spring_ndvi')
ndvi_min_e = s2_early.select('ndvi_min')
ndvi_min_l = s2_late.select('ndvi_min')
ndviDrop = ndvi_e.subtract(ndvi_l)

# ESA WorldCover 10m (2021) como desempate na zona ambigua
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(porto)
esaBuilt = esa.eq(50)

# Classificacao: temporal + espectral
# arvore = NDVI verao >= 0.5
#          AND NDVI primavera (Mai-Jun, p15) >= 0.7  [relva seca, arvores com folha]
#          AND NDVI min (p10) >= 0.3                  [tolerante para caducifolias]
#          AND NIR/Green >= 4                          [filtra relva regada]
#          AND B3 < 600                                [filtra vegetacao brilhante]
def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min):
    # Arvores puras (rigoroso)
    # B3<600 OU (B3<800 se NDVI_min>=0.5) - arvores claras com NDVI estavel
    b3_ok = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isTreeStrict = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok)
    )
    # Verde urbano / arvores mistas (ruas arborizadas, jardins)
    b3_ok_mixed = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTreeStrict.Not())
    )
    # Arvores = puras + mistas (juntas para o mapa)
    isTree = isTreeStrict.Or(isMixed)
    # Edificado
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    # Solo/Relva = resto
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isTreeStrict, isMixed, isBuilt, isSolo

isTree_e, _, _, isBuilt_e, isSolo_e = classify(ndvi_e, ndbi_e, nirgreen_e, green_e, spring_ndvi_e, ndvi_min_e)
isTree_l_base, _, _, isBuilt_l_base, _ = classify(ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l)

# Criterio restrito: pixel edificado em 2016 so sai se NDVI 2025 >= 0.45
stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isSolo_l = isTree_l.Not().And(isBuilt_l.Not())

treesToSolo  = isTree_e.And(isSolo_l).And(ndviDrop.gte(0.15))
treesToBuilt = isTree_e.And(isBuilt_l).And(ndviDrop.gte(0.15))
soloToBuilt  = isSolo_e.And(isBuilt_l).And(ndviDrop.gte(0.1))
soloToTrees  = isTree_e.Not().And(isTree_l).And(ndvi_l.subtract(ndvi_e).gte(0.15))

os.makedirs('layers', exist_ok=True)
DIM = 2048

def download_layer(image, color_hex, filename):
    """Download layer as colored PNG with transparency."""
    from PIL import Image
    import io, time

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

    # Make black/near-black pixels transparent
    pixels = list(img.getdata())
    new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
    img.putdata(new_data)
    img.save(filepath)
    print(f'  {filename} guardado ({os.path.getsize(filepath)//1024} KB)')
    return filepath

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

# Layers: (id, ee_image, label, default_color, show_by_default)
LANDUSE_LAYERS = [
    ('uso_arvores',   isTree_l.selfMask(),  u'\u00c1rvores (2024-25)',   '228B22', False),
    ('uso_solo',      isSolo_l.selfMask(),  u'Solo (2024-25)',           'C2B280', False),
    ('uso_edificado', isBuilt_l.selfMask(), u'Edificado (2024-25)',      '888888', False),
]

TRANS_LAYERS = [
    ('arvores_edificado', treesToBuilt.selfMask(), u'\u00c1rvores \u2192 Edificado',  'D7263D', True),
    ('arvores_solo',      treesToSolo.selfMask(),  u'\u00c1rvores \u2192 Solo',       'E8A838', True),
    ('solo_edificado',    soloToBuilt.selfMask(),  u'Solo \u2192 Edificado',          '6A1B9A', True),
    ('solo_arvores',      soloToTrees.selfMask(),  u'Solo \u2192 \u00c1rvores',       '2E7D32', True),
]

ALL_LAYERS = LANDUSE_LAYERS + TRANS_LAYERS

print('\nA descarregar camadas...')
for lid, mask, label, color, show in ALL_LAYERS:
    download_layer(mask, color, f'{lid}.png')

muni_styled = ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=2)
download_layer(muni_styled, 'FFFFFF', 'municipios.png')

# ============================================================
# Build HTML (pure Leaflet, single panel)
# ============================================================
print('\nA construir mapa...')

# Add municipios to layers
muni_styled = ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=2)
download_layer(muni_styled, 'FFFFFF', 'municipios.png')

ALL_LAYERS_PLUS = ALL_LAYERS + [('municipios', None, 'Limites municipais', 'FFFFFF', True)]

# Build layer JS data
import json
layers_js_items = []
for lid, mask, label, color, show in ALL_LAYERS_PLUS:
    b64 = to_base64(f'layers/{lid}.png')
    layers_js_items.append(
        f'{{id:"{lid}",label:"{label}",color:"#{color}",show:{str(show).lower()},src:"{b64}"}}'
    )
layers_js = ',\n'.join(layers_js_items)

n_landuse = len(LANDUSE_LAYERS)
n_trans = len(TRANS_LAYERS)

basemaps = [
    ('CartoDB Dark', 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'),
    ('CartoDB Positron', 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png'),
    ('Satelite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'),
    ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'),
]
basemap_options = ''.join(
    f'<option value="{url}"{"selected" if i==0 else ""}>{name}</option>'
    for i, (name, url) in enumerate(basemaps)
)

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Espaco verde do Porto - Mudanca 2016-2025</title>
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
</style>
</head>
<body>
<div id="nav">
  <a href="index.html">Início</a>
  <a href="mapa.html" class="active">Mapa 2016-2025</a>
  <a href="ndvi_historico.html">Hist&oacute;rico 1947-2024</a>
  <a href="interiores_quarteiroes.html">Verde Privado</a>
  <a href="atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Espaco verde do Porto</b><br>
  <span style="color:#aaa;font-size:10px;">2016-17 &rarr; 2024-25 &bull; Sentinel-2 10m</span>

  <div class="section">Uso do solo (2024-25)</div>
  <div id="landuse-rows"></div>

  <div class="section">Transicoes (2016 &rarr; 2025)</div>
  <div id="trans-rows"></div>

  <div class="section">Outros</div>
  <div id="other-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">Fonte: Sentinel-2 (ESA) &bull; Copernicus</span>
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
  var nLanduse = {n_landuse};
  var nTrans = {n_trans};
  var divLanduse = document.getElementById('landuse-rows');
  var divTrans = document.getElementById('trans-rows');
  var divOther = document.getElementById('other-rows');

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

    var cp = document.createElement('input');
    cp.type = 'color'; cp.value = L_.color; cp.dataset.idx = i;
    cp.addEventListener('input', function() {{
      var idx = +this.dataset.idx;
      var s = state[idx];
      s.color = this.value;
      s.overlay.setUrl(renderColored(s.mask, this.value));
    }});

    var lb = document.createElement('label');
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';

    row.appendChild(cb);
    row.appendChild(cp);
    row.appendChild(lb);

    if (i < nLanduse) divLanduse.appendChild(row);
    else if (i < nLanduse + nTrans) divTrans.appendChild(row);
    else divOther.appendChild(row);
  }}
}}

init();
</script>
<div style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
</body>
</html>'''

output = 'index.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)
