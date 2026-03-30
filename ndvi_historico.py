"""
NDVI historico do Porto (1947-2024).
Combina classificacao 1947 (ortofoto CIIMAR/FCUP) com Landsat 5/8/9.
"""
import ee
import requests
import os
import math
import base64
import io
import time
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Mesma area do projecto original
porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

# --- 1947 config (ortofoto CIIMAR/FCUP) ---
WMS_1947_URL = 'https://gis.ciimar.up.pt/porto/wms'
WMS_1947_LAYER = 'Orto_Porto_1947'
# Bounds do mosaico 1947 (calculados em orto_1947.py)
_BBOX_3857 = {'xmin': -968578.0, 'ymin': 5031536.0, 'xmax': -950671.0, 'ymax': 5040407.0}
_TILE_SIZE_M, _TILE_PX = 1000, 2048
_ntx = math.ceil((_BBOX_3857['xmax'] - _BBOX_3857['xmin']) / _TILE_SIZE_M)
_nty = math.ceil((_BBOX_3857['ymax'] - _BBOX_3857['ymin']) / _TILE_SIZE_M)
_mx = _BBOX_3857['xmin'] + _ntx * _TILE_SIZE_M
_my = _BBOX_3857['ymax'] - _nty * _TILE_SIZE_M
def _m3857_to_wgs84(x, y):
    lon = x / 20037508.34 * 180.0
    lat = math.degrees(2 * math.atan(math.exp(y * math.pi / 20037508.34)) - math.pi / 2)
    return lat, lon
_lat_s, _lon_w = _m3857_to_wgs84(_BBOX_3857['xmin'], _my)
_lat_n, _lon_e = _m3857_to_wgs84(_mx, _BBOX_3857['ymax'])
BOUNDS_1947 = [[_lat_s, _lon_w], [_lat_n, _lon_e]]
LAYERS_1947 = [
    ('uso_1947_vegetacao', 'Vegetacao 1947', '#228B22', True),
    ('uso_1947_edificado', 'Edificado 1947', '#888888', True),
]

# Municipios para fronteiras
municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

# Concelho do Porto (para mascarar edificado — exclui agua do mar/rio)
portoMuni = municipios.filter(ee.Filter.eq('municipio', 'Porto'))
portoMuniGeom = portoMuni.geometry()

# ============================================================
# Epocas: janelas de 5-6 anos para maximizar cenas disponiveis
# ============================================================
EPOCHS = [
    ('1972-76',  'MSS',        [1972, 1973, 1974, 1975, 1976]),
    ('1985-90',  'Landsat 5',  [1985, 1986, 1987, 1988, 1989, 1990]),
    ('1995-00',  'Landsat 5',  [1995, 1996, 1997, 1998, 1999, 2000]),
    ('2001-05',  'Landsat 5',  [2001, 2002, 2003, 2004, 2005]),
    ('2016-17',  'Landsat 8',  [2016, 2017]),
    ('2023-24',  'Landsat 8',  [2023, 2024]),
]

# ============================================================
# Funcoes de processamento Landsat
# ============================================================

def cloud_mask_mss(img):
    """Cloud mask basica para Landsat 1-2 MSS Collection 2."""
    qa = img.select('QA_PIXEL')
    cloud = qa.bitwiseAnd(1 << 3).eq(0)
    return img.updateMask(cloud)

def ndvi_mss(img):
    """NDVI para Landsat 1-2 MSS (B6=NIR 0.7-0.8um, B5=Red 0.6-0.7um).
    DNs brutos (sem factor de escala) — a normalizacao PIF corrige."""
    img = cloud_mask_mss(img)
    nir = img.select('B6').toFloat()
    red = img.select('B5').toFloat()
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
    return ndvi.clamp(-1, 1)

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
    """NDVI para Landsat 8/9 OLI, harmonizado para nivel TM (Roy et al. 2016).

    Coeficientes OLI->ETM+ (slope, intercept) por banda:
      Red (B4):  0.9585, -0.0002
      NIR (B5):  0.9785, -0.0010
    Aplicados apos conversao a reflectancia de superficie.
    """
    img = cloud_mask_l8(img)
    nir_raw = img.select('SR_B5').multiply(0.0000275).add(-0.2)
    red_raw = img.select('SR_B4').multiply(0.0000275).add(-0.2)
    # Harmonizar OLI -> TM (Roy et al. 2016, Table 2)
    red = red_raw.multiply(0.9585).add(-0.0002)
    nir = nir_raw.multiply(0.9785).add(-0.0010)
    ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
    return ndvi.clamp(-1, 1)

def get_ndvi_composite(sensor, years):
    """Composito NDVI mediana de verao (Jun-Set) para varios anos."""
    cols = []
    for year in years:
        start = f'{year}-06-01'
        end = f'{year}-09-30'
        if sensor == 'MSS':
            # Landsat 1 MSS (1972-1978) — T1 + T2 para maximizar cenas
            col = (ee.ImageCollection('LANDSAT/LM01/C02/T1')
                .filterBounds(porto)
                .filterDate(start, end)
                .map(ndvi_mss))
            col_t2 = (ee.ImageCollection('LANDSAT/LM01/C02/T2')
                .filterBounds(porto)
                .filterDate(start, end)
                .map(ndvi_mss))
            col = col.merge(col_t2)
            # Landsat 2 MSS (1975-1982) — apenas T2 disponivel
            if year >= 1975:
                col2 = (ee.ImageCollection('LANDSAT/LM02/C02/T2')
                    .filterBounds(porto)
                    .filterDate(start, end)
                    .map(ndvi_mss))
                col = col.merge(col2)
        elif sensor == 'Landsat 5':
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
# Alvos pseudo-invariantes (PIF) para normalizacao inter-sensor
# Buffer de 60m (~2 pixeis Landsat) a volta de cada ponto
# ============================================================
PIF_BUFFER = 60  # metros

PIF_POINTS = {
    'floresta': [
        ee.Geometry.Point([-8.657919, 41.157911]).buffer(PIF_BUFFER),  # Serralves
        ee.Geometry.Point([-8.677261, 41.168894]).buffer(PIF_BUFFER),  # Parque Cidade
    ],
    'solo_relva': [
        ee.Geometry.Point([-8.658664, 41.163311]).buffer(PIF_BUFFER),
        ee.Geometry.Point([-8.588781, 41.144906]).buffer(PIF_BUFFER),
    ],
    'agua': [
        ee.Geometry.Point([-8.586953, 41.140633]).buffer(PIF_BUFFER),  # Douro/Foz
        ee.Geometry.Point([-8.683278, 41.149100]).buffer(PIF_BUFFER),  # Mar
    ],
}

# Juntar todos os pontos PIF numa FeatureCollection para extraccao
pif_features = []
for pif_type, geoms in PIF_POINTS.items():
    for i, geom in enumerate(geoms):
        pif_features.append(ee.Feature(geom, {'type': pif_type, 'idx': i}))
pif_fc = ee.FeatureCollection(pif_features)

# ============================================================
# Calcular compositos (antes da normalizacao)
# ============================================================
print('A calcular compositos NDVI por epoca...')
composites_raw = {}
for name, sensor, years in EPOCHS:
    ndvi, count = get_ndvi_composite(sensor, years)
    n = count.getInfo()
    print(f'  {name} ({sensor}): {n} cenas')
    composites_raw[name] = ndvi

# ============================================================
# Normalizacao PIF: ajustar todas as epocas ao nivel da referencia
# Referencia = primeira epoca (1985-90, Landsat 5)
# ============================================================
print('\nA extrair NDVI nos pontos PIF...')
REF_EPOCH = '1985-90'  # Referencia fixa: Landsat 5 SR (nao MSS DN)

def extract_pif_values(composite, epoch_name):
    """Extrai NDVI medio em cada ponto PIF."""
    values = {}
    for pif_type, geoms in PIF_POINTS.items():
        type_vals = []
        for geom in geoms:
            val = composite.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=30,
            ).getInfo().get('ndvi', None)
            if val is not None:
                type_vals.append(val)
        values[pif_type] = sum(type_vals) / len(type_vals) if type_vals else None
    return values

# Extrair valores PIF para todas as epocas
pif_values = {}
for name, sensor, years in EPOCHS:
    pif_values[name] = extract_pif_values(composites_raw[name], name)
    print(f'  {name}: agua={pif_values[name]["agua"]:.4f}  '
          f'solo={pif_values[name]["solo_relva"]:.4f}  '
          f'floresta={pif_values[name]["floresta"]:.4f}')

# Calcular normalizacao linear por minimos quadrados
# Para cada epoca: NDVI_norm = slope * NDVI_raw + intercept
# onde slope e intercept minimizam o erro vs os valores de referencia
print('\nA calcular coeficientes de normalizacao...')
ref_vals = pif_values[REF_EPOCH]
ref_points = [ref_vals['agua'], ref_vals['solo_relva'], ref_vals['floresta']]

composites = {}
for name, sensor, years in EPOCHS:
    if name == REF_EPOCH:
        composites[name] = composites_raw[name]
        print(f'  {name}: referencia (sem ajuste)')
        continue

    epoch_vals = pif_values[name]
    raw_points = [epoch_vals['agua'], epoch_vals['solo_relva'], epoch_vals['floresta']]

    # Regressao linear: ref = slope * raw + intercept
    n = len(raw_points)
    sum_x = sum(raw_points)
    sum_y = sum(ref_points)
    sum_xy = sum(x * y for x, y in zip(raw_points, ref_points))
    sum_xx = sum(x * x for x in raw_points)
    slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
    intercept = (sum_y - slope * sum_x) / n

    print(f'  {name}: slope={slope:.4f}  intercept={intercept:+.4f}')

    # Aplicar normalizacao
    composites[name] = composites_raw[name].multiply(slope).add(intercept).clamp(-1, 1)

# Verificar valores normalizados
print('\nA verificar normalizacao...')
for name, sensor, years in EPOCHS:
    vals = extract_pif_values(composites[name], name)
    print(f'  {name}: agua={vals["agua"]:.4f}  '
          f'solo={vals["solo_relva"]:.4f}  '
          f'floresta={vals["floresta"]:.4f}')

# ============================================================
# Download das camadas
# ============================================================
os.makedirs('layers_historico', exist_ok=True)
DIM = 2048

# Paleta NDVI: castanho -> amarelo -> verde escuro
NDVI_PALETTE = ['8B4513', 'D2B48C', 'F5DEB3', 'FFFF00', 'ADFF2F', '32CD32', '228B22', '006400']

def _robust_download(vis_image, filepath, label, transparent_black=False):
    """Download robusto com retry e backoff exponencial."""
    from PIL import Image as PILImage

    if os.path.exists(filepath):
        print(f'  {os.path.basename(filepath)} ja existe, a saltar...')
        return filepath

    for attempt in range(5):
        try:
            wait = 3 * (2 ** attempt) if attempt > 0 else 0
            if wait:
                print(f'  Retry {attempt+1}/5 apos {wait}s...')
                time.sleep(wait)
            url = vis_image.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
            print(f'  A descarregar {label}...')
            r = requests.get(url, timeout=120)
            img = PILImage.open(io.BytesIO(r.content)).convert('RGBA')
            if transparent_black:
                pixels = list(img.getdata())
                new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
                img.putdata(new_data)
            img.save(filepath)
            print(f'  {os.path.basename(filepath)} guardado ({os.path.getsize(filepath)//1024} KB)')
            return filepath
        except Exception as e:
            print(f'  Tentativa {attempt+1} falhou: {e}')
            if attempt == 4:
                print(f'  ERRO: nao foi possivel descarregar {label}')
                return None

def download_ndvi(image, filename, label):
    vis = image.visualize(min=0, max=0.8, palette=NDVI_PALETTE)
    return _robust_download(vis, f'layers_historico/{filename}', label)

def download_mask(image, color_hex, filename):
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    return _robust_download(vis, f'layers_historico/{filename}', filename, transparent_black=True)

# ============================================================
# Mascaras de vegetacao (NDVI >= 0.4) por epoca
# ============================================================
NDVI_VEG_THRESHOLD = 0.25

veg_masks = {}
for name, sensor, years in EPOCHS:
    veg_masks[name] = composites[name].gte(NDVI_VEG_THRESHOLD)

# Mascara de agua permanente (JRC Global Surface Water)
# occurrence > 50% = agua permanente (rio Douro, mar, etc.)
# unmask(0) garante que pixeis sem dados JRC ficam como 0 (nao-agua)
jrc_water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
water_mask = jrc_water.unmask(0).gt(50).clip(porto)  # 1 = agua, 0 = nao-agua

# Mascaras de edificado (tudo o que nao e vegetacao nem agua)
portoMuniMask = ee.Image.constant(1).clip(portoMuniGeom)
edif_masks = {}
for name, sensor, years in EPOCHS:
    not_veg = veg_masks[name].Not()
    edif_masks[name] = not_veg.updateMask(water_mask.Not()).updateMask(portoMuniMask)

# Perda/ganho de vegetacao (primeira vs ultima epoca)
first_epoch = EPOCHS[0][0]   # 1985-90
last_epoch = EPOCHS[-1][0]   # 2023-24
veg_loss = veg_masks[first_epoch].And(veg_masks[last_epoch].Not()).selfMask()
veg_gain = veg_masks[first_epoch].Not().And(veg_masks[last_epoch]).selfMask()

# ============================================================
# Downloads (com pausa entre pedidos para evitar desconexoes)
# ============================================================
DOWNLOAD_PAUSE = 5  # segundos entre downloads

# NDVI por epoca
print('\nA descarregar camadas NDVI...')
for name, sensor, years in EPOCHS:
    download_ndvi(composites[name], f'ndvi_{name}.png', f'NDVI {name}')
    time.sleep(DOWNLOAD_PAUSE)

# Mascaras de vegetacao por epoca
print('\nA descarregar mascaras de vegetacao...')
for name, sensor, years in EPOCHS:
    download_mask(veg_masks[name].selfMask(), '00FF00', f'veg_{name}.png')
    time.sleep(DOWNLOAD_PAUSE)

# Mascaras de edificado por epoca
print('\nA descarregar mascaras de edificado...')
for name, sensor, years in EPOCHS:
    download_mask(edif_masks[name].selfMask(), 'C4A882', f'edif_{name}.png')
    time.sleep(DOWNLOAD_PAUSE)

# Perda e ganho
print('\nA descarregar perda/ganho de vegetacao...')
download_mask(veg_loss, 'FF4444', 'veg_perda.png')
time.sleep(DOWNLOAD_PAUSE)
download_mask(veg_gain, '44FF44', 'veg_ganho.png')
time.sleep(DOWNLOAD_PAUSE)

# Municipios
print('\nA descarregar limites...')
muni_styled = ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=2)
download_mask(muni_styled, 'FFFFFF', 'municipios.png')

# ============================================================
# Estatisticas: NDVI medio + area de vegetacao por epoca
# ============================================================
PIXEL_AREA_HA = 30 * 30 / 10000  # 30m pixel = 0.09 ha

print('\n--- Estatisticas por epoca ---')
print(f'  {"Epoca":<12} {"NDVI medio":>12} {"Area veg (ha)":>14} {"Area veg (%)":>13}')
print(f'  {"-"*12} {"-"*12} {"-"*14} {"-"*13}')

# Area total da regiao (pixeis validos)
total_pixels = composites[first_epoch].gt(-1).reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)

for name, sensor, years in EPOCHS:
    stats = composites[name].reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=porto,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    veg_count = veg_masks[name].reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=porto,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    ndvi_mean = stats.get('ndvi', 0)
    veg_pixels = veg_count.get('ndvi', 0)
    veg_ha = veg_pixels * PIXEL_AREA_HA
    veg_pct = (veg_pixels / total_pixels * 100) if total_pixels > 0 else 0
    print(f'  {name:<12} {ndvi_mean:>12.4f} {veg_ha:>13.0f} {veg_pct:>12.1f}%')

# Perda/ganho totais
loss_count = veg_loss.unmask(0).reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)
gain_count = veg_gain.unmask(0).reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)
print(f'\n  Vegetacao perdida ({first_epoch} -> {last_epoch}): {loss_count * PIXEL_AREA_HA:.0f} ha')
print(f'  Vegetacao ganha  ({first_epoch} -> {last_epoch}): {gain_count * PIXEL_AREA_HA:.0f} ha')
print(f'  Balanco liquido: {(gain_count - loss_count) * PIXEL_AREA_HA:+.0f} ha')

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

VEG_LAYERS = []
for name, sensor, years in EPOCHS:
    yr_range = f'{years[0]}-{years[-1]}'
    VEG_LAYERS.append((f'veg_{name}', f'Vegetacao {yr_range}', False))

EDIF_LAYERS = []
for name, sensor, years in EPOCHS:
    yr_range = f'{years[0]}-{years[-1]}'
    EDIF_LAYERS.append((f'edif_{name}', f'Edificado {yr_range}', False))

CHANGE_LAYERS_INFO = [
    ('veg_perda', 'Perda de vegetacao (85-90 \u2192 23-24)', False),
    ('veg_ganho', 'Ganho de vegetacao (85-90 \u2192 23-24)', False),
]

ALL_MAP_LAYERS = (NDVI_LAYERS + VEG_LAYERS + EDIF_LAYERS + CHANGE_LAYERS_INFO
    + [('municipios', 'Limites municipais', True)])

layers_js_items = []
for lid, label, show in ALL_MAP_LAYERS:
    b64 = to_base64(f'layers_historico/{lid}.png')
    layers_js_items.append(
        '{' + f'id:"{lid}",label:"{label}",show:{str(show).lower()},src:"{b64}"' + '}'
    )
layers_js = ',\n'.join(layers_js_items)

n_ndvi = len(NDVI_LAYERS)
n_veg = len(VEG_LAYERS)
n_edif = len(EDIF_LAYERS)
n_change = len(CHANGE_LAYERS_INFO)

# Layers 1947 (base64, reduzidas para caber no canvas do browser)
def to_base64_resized(filepath, scale=0.25):
    """Reduz imagem para evitar limites de canvas do browser."""
    img = Image.open(filepath)
    new_size = (img.width // int(1/scale), img.height // int(1/scale))
    img = img.resize(new_size, Image.NEAREST)
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

layers1947_js_items = []
for lid, label, color, show in LAYERS_1947:
    b64 = to_base64_resized(f'1947/layers/{lid}.png')
    layers1947_js_items.append(
        '{' + f'id:"{lid}",label:"{label}",color:"{color}",show:{str(show).lower()},src:"{b64}"' + '}'
    )
layers1947_js = ',\n'.join(layers1947_js_items)

basemaps = [
    ('CartoDB Dark', 'dark'),
    ('CartoDB Positron', 'positron'),
    ('Ortofoto 1947', 'orto1947'),
    ('Satelite', 'satellite'),
    ('OpenStreetMap', 'osm'),
]
basemap_options = ''.join(
    f'<option value="{key}"{"selected" if i==0 else ""}>{name}</option>'
    for i, (name, key) in enumerate(basemaps)
)

html = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Vegetacao do Porto 1947-2024</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body { margin:0; }
  #map { position:absolute; top:0; bottom:0; width:100%; }
  #panel {
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); min-width:320px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }
  .row { display:flex; align-items:center; gap:6px; margin:2px 0; }
  .row input[type=color] { width:22px; height:22px; border:none; cursor:pointer; padding:0; }
  .row input[type=checkbox] { width:15px; height:15px; cursor:pointer; margin:0; }
  .row label { cursor:pointer; font-size:12px; }
  .section { font-size:11px; color:#aaa; font-weight:bold; margin:8px 0 4px 0; }
  select { background:#333; color:#eee; border:1px solid #555; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }
  .swatch { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; }
  #nav {
    position:fixed; top:10px; right:10px; z-index:1000;
    display:flex; gap:6px; font:11px 'Segoe UI',Arial,sans-serif;
  }
  #nav a {
    background:rgba(255,255,255,0.9); color:#444; text-decoration:none;
    padding:4px 10px; border-radius:5px; box-shadow:0 1px 4px rgba(0,0,0,0.15);
  }
  #nav a:hover { background:#fff; color:#222; }
  #nav a.active { background:#2E7D32; color:#fff; }
</style>
</head>
<body>
<div id="nav">
  <a href="index.html">Início</a>
  <a href="mapa.html">Mapa 2016-2025</a>
  <a href="ndvi_historico.html" class="active">Hist&oacute;rico 1947-2024</a>
  <a href="interiores_quarteiroes.html">Verde Privado</a>
  <a href="acessibilidade/acessibilidade_verde.html">Acessibilidade</a>
  <a href="atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Vegetacao do Porto</b><br>
  <span style="color:#aaa;font-size:10px;">1947-2024 &bull; Ortofoto 1947 + Landsat MSS 60m / TM-OLI 30m</span>

  <div class="section">Uso do solo 1947 (Ortofoto)</div>
  <div id="uso1947-rows"></div>

  <div class="section">Mascara de vegetacao por epoca</div>
  <div id="veg-rows"></div>

  <div class="section">Mascara de edificado por epoca</div>
  <div id="edif-rows"></div>

  <div class="section">Perda e ganho (1985-90 vs 2023-24)</div>
  <div id="change-rows"></div>
  <div style="font-size:10px;color:#888;margin:4px 0;">
    <span class="swatch" style="background:#FF4444;"></span>Perda
    <span class="swatch" style="background:#44FF44;margin-left:10px;"></span>Ganho
  </div>

  <div class="section">Outros</div>
  <div id="other-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">''' + basemap_options + '''</select>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">
    Fonte: Ortofotomapa 1947 (CIIMAR/FCUP) &bull; Landsat MSS/TM/OLI (USGS/NASA)<br>
    1947: Pixel RF (textura local) &bull; Historico: NDVI &ge; 0.25 &bull; Roy et al. 2016<br>
    Limites: CAOP 2025 (DGT)
  </span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {maxZoom:19, attribution:''}).addTo(map);
var wmsLayer = null;

document.getElementById('basemap-select').addEventListener('change', function() {
  if (baseTile) { map.removeLayer(baseTile); baseTile = null; }
  if (wmsLayer) { map.removeLayer(wmsLayer); wmsLayer = null; }
  var v = this.value;
  if (v === 'orto1947') {
    wmsLayer = L.tileLayer.wms("''' + WMS_1947_URL + '''", {
      layers: "''' + WMS_1947_LAYER + '''", format: 'image/png', transparent: false,
      version: '1.1.1', maxZoom: 20, attribution: 'CIIMAR/FCUP'
    }).addTo(map);
  } else {
    var urls = {
      dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      positron: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      osm: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    };
    baseTile = L.tileLayer(urls[v], {maxZoom:19, attribution:''}).addTo(map);
  }
});

// --- 1947 layers (color picker) ---
var bounds1947 = ''' + str(BOUNDS_1947) + ''';
var layers1947 = [''' + layers1947_js + '''];
var overlays1947 = [];

function hexToRgb(h) {
  h = h.replace('#','');
  return [parseInt(h.substring(0,2),16), parseInt(h.substring(2,4),16), parseInt(h.substring(4,6),16)];
}

function extractMask(src) {
  return new Promise(function(r) {
    var i = new Image();
    i.onload = function() {
      var c = document.createElement('canvas');
      c.width = i.width; c.height = i.height;
      var x = c.getContext('2d');
      x.drawImage(i, 0, 0);
      var d = x.getImageData(0, 0, c.width, c.height);
      var a = new Uint8Array(d.data.length / 4);
      for (var j = 0; j < a.length; j++) a[j] = d.data[j * 4 + 3];
      r({w: c.width, h: c.height, alpha: a});
    };
    i.src = src;
  });
}

function renderColored(m, hex) {
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = m.w; c.height = m.h;
  var x = c.getContext('2d');
  var d = x.createImageData(m.w, m.h);
  for (var i = 0; i < m.alpha.length; i++) {
    d.data[i*4] = rgb[0]; d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2]; d.data[i*4+3] = m.alpha[i];
  }
  x.putImageData(d, 0, 0);
  return c.toDataURL();
}

// --- Historico layers ---
var boundsH = ''' + str(BOUNDS) + ''';
var layersH = [''' + layers_js + '''];
var overlaysH = [];
var nNdvi = ''' + str(n_ndvi) + ''';
var nVeg = ''' + str(n_veg) + ''';
var nEdif = ''' + str(n_edif) + ''';
var nChange = ''' + str(n_change) + ''';

function makeCheckbox(container, idx, defaultOn) {
  var row = document.createElement('div');
  row.className = 'row';
  var cb = document.createElement('input');
  cb.type = 'checkbox'; cb.checked = defaultOn; cb.dataset.idx = idx;
  if (defaultOn) overlaysH[idx].addTo(map);
  cb.addEventListener('change', function() {
    var i = +this.dataset.idx;
    if (this.checked) overlaysH[i].addTo(map);
    else map.removeLayer(overlaysH[i]);
  });
  var lb = document.createElement('label');
  lb.textContent = layersH[idx].label;
  row.appendChild(cb);
  row.appendChild(lb);
  container.appendChild(row);
}

async function init() {
  // --- Init 1947 layers ---
  var div1947 = document.getElementById('uso1947-rows');
  for (var i = 0; i < layers1947.length; i++) {
    var L_ = layers1947[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds1947);
    if (L_.show) ov.addTo(map);
    overlays1947.push({overlay: ov, mask: m, color: L_.color, visible: L_.show});

    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {
      var idx = +this.dataset.idx;
      overlays1947[idx].visible = this.checked;
      if (this.checked) overlays1947[idx].overlay.addTo(map);
      else map.removeLayer(overlays1947[idx].overlay);
    });
    var cp = document.createElement('input');
    cp.type = 'color'; cp.value = L_.color; cp.dataset.idx = i;
    cp.addEventListener('input', function() {
      var idx = +this.dataset.idx;
      var s = overlays1947[idx];
      s.color = this.value;
      s.overlay.setUrl(renderColored(s.mask, this.value));
    });
    var lb = document.createElement('label');
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(cp); row.appendChild(lb);
    div1947.appendChild(row);
  }

  // --- Init historico layers ---
  for (var i = 0; i < layersH.length; i++) {
    var ov = L.imageOverlay(layersH[i].src, boundsH);
    overlaysH.push(ov);
  }

  // NDVI checkboxes (exclusive)
  var divNdvi = document.getElementById('ndvi-rows');
  if (divNdvi) {
    for (var i = 0; i < nNdvi; i++) {
      var row = document.createElement('div');
      row.className = 'row';
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = (i === nNdvi - 1); cb.dataset.idx = i;
      if (i === nNdvi - 1) overlaysH[i].addTo(map);
      cb.addEventListener('change', function() {
        var idx = +this.dataset.idx;
        if (this.checked) {
          for (var j = 0; j < nNdvi; j++) {
            if (j !== idx) {
              map.removeLayer(overlaysH[j]);
              divNdvi.querySelectorAll('input[type=checkbox]')[j].checked = false;
            }
          }
          overlaysH[idx].addTo(map);
        } else {
          map.removeLayer(overlaysH[idx]);
        }
      });
      var lb = document.createElement('label');
      lb.textContent = layersH[i].label;
      row.appendChild(cb);
      row.appendChild(lb);
      divNdvi.appendChild(row);
    }
  }

  // Vegetation masks
  var divVeg = document.getElementById('veg-rows');
  for (var i = nNdvi; i < nNdvi + nVeg; i++) {
    makeCheckbox(divVeg, i, false);
  }

  // Edificado masks
  var divEdif = document.getElementById('edif-rows');
  var edifStart = nNdvi + nVeg;
  for (var i = edifStart; i < edifStart + nEdif; i++) {
    makeCheckbox(divEdif, i, false);
  }

  // Change layers (loss/gain)
  var divChange = document.getElementById('change-rows');
  var changeStart = edifStart + nEdif;
  for (var i = changeStart; i < changeStart + nChange; i++) {
    makeCheckbox(divChange, i, false);
  }

  // Other layers (municipios)
  var divOther = document.getElementById('other-rows');
  var otherStart = changeStart + nChange;
  for (var i = otherStart; i < layersH.length; i++) {
    makeCheckbox(divOther, i, layersH[i].show);
  }
}

init();
</script>
<div style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
</body>
</html>'''

output = 'ndvi_historico.html'
with open(output, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open(output)
