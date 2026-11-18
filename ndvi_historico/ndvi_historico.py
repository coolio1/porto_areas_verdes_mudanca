"""
NDVI historico do Porto (1947-2024).
Combina classificacao 1947 (ortofoto CIIMAR/FCUP) com Landsat 5/8/9.
"""
import ee
import requests
import os
import math
import io
import time
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
LAYERS_DIR = os.path.join(ROOT_DIR, 'layers_historico')

load_dotenv(os.path.join(ROOT_DIR, '..', '.env'))  # global (OneDrive\Claude\.env); o local abaixo sobrepõe
load_dotenv(os.path.join(ROOT_DIR, '.env'))
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
    # 1972-76 (MSS) retirado em 2026-11-11: o limiar de NDVI não é transferível entre sensores/bandas MSS
    # (29-69 % de vegetação conforme a banda), logo não é comparável com o TM. As funções *_mss ficam abaixo, sem uso.
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
    """NDVI para Landsat 8/9 OLI (SR_B5=NIR, SR_B4=Red), reflectancia de superficie C2.

    Sem harmonizacao de Roy et al. 2016 (retirada em 2026-11-18): os coeficientes que aqui estavam
    (0.9585/0.9785) nao eram os de Roy para NDVI e a Google nao a recomenda na Colecao 2 SR. A diferenca
    de sensor corrige-se com o desvio medido na sobreposicao L7/L8 (OFFSET_OLI, abaixo).
    """
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
# Compositos por epoca + ponte Landsat 7 (desvio de sensor)
# ============================================================
# A normalizacao PIF (regressao em 3 tipos de alvo) foi retirada em 2026-11-18: criava uma queda
# artificial de ~14 p.p. na vegetacao 1985-90 -> 2023-24 que as medicoes ano a ano nao confirmam.
# Agora: Landsat 5 fica em bruto (L5 ~ L7: 49,8 vs 49,5 % em 1999-2011) e o OLI (L8/9) recebe um
# desvio aditivo de NDVI, medido na sobreposicao L7/L8 (2013-2021) sobre o concelho.
# Evidencia: ndvi_historico/diagnostico_anos.py (% de vegetacao ano a ano).
PONTE_ANOS = list(range(2013, 2022))   # L7 e L8 em simultaneo (L9 so desde 2021)

def ndvi_l7(img):
    """NDVI para Landsat 7 ETM+ (mesmas bandas e escala do TM)."""
    return ndvi_l5(img)

def composito_l7(years):
    cols = None
    for year in years:
        c = (ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
             .filterBounds(porto).filterDate(f'{year}-06-01', f'{year}-09-30')
             .filter(ee.Filter.lt('CLOUD_COVER', 40)).map(ndvi_l7))
        cols = c if cols is None else cols.merge(c)
    return cols.median().clip(porto)

def composito_l8_so(years):
    cols = None
    for year in years:
        c = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
             .filterBounds(porto).filterDate(f'{year}-06-01', f'{year}-09-30')
             .filter(ee.Filter.lt('CLOUD_COVER', 40)).map(ndvi_l8))
        cols = c if cols is None else cols.merge(c)
    return cols.median().clip(porto)

def media_concelho(img):
    return img.reduceRegion(ee.Reducer.mean(), portoMuniGeom, 30, maxPixels=1e9).get('ndvi').getInfo()

print('A medir o desvio de sensor L8-L7 na sobreposicao', PONTE_ANOS[0], '-', PONTE_ANOS[-1], '...')
_l7 = composito_l7(PONTE_ANOS)
_l8 = composito_l8_so(PONTE_ANOS)
OFFSET_OLI = media_concelho(_l8.subtract(_l7).rename('ndvi'))
print(f'  desvio NDVI (L8 - L7, media do concelho) = {OFFSET_OLI:+.4f}')
_pct = lambda im: 100 * im.gte(0.25).rename('ndvi').reduceRegion(
    ee.Reducer.mean(), portoMuniGeom, 30, maxPixels=1e9).get('ndvi').getInfo()
print(f'  % vegetacao na sobreposicao: L7={_pct(_l7):.1f}  L8 bruto={_pct(_l8):.1f}  '
      f'L8 corrigido={_pct(_l8.subtract(OFFSET_OLI)):.1f}')

print('\nA calcular compositos NDVI por epoca...')
composites = {}
for name, sensor, years in EPOCHS:
    ndvi, count = get_ndvi_composite(sensor, years)
    n = count.getInfo()
    if sensor == 'Landsat 8':
        ndvi = ndvi.subtract(OFFSET_OLI).clamp(-1, 1)
        print(f'  {name} ({sensor}): {n} cenas, desvio {-OFFSET_OLI:+.4f} aplicado')
    else:
        print(f'  {name} ({sensor}): {n} cenas, sem ajuste')
    composites[name] = ndvi

# ============================================================
# Incerteza por epoca (2026-11-18): dispersao ano a ano da % de vegetacao dentro de cada epoca
# (mesmo metodo, 1 compósito por ano) e erro da ponte L8-L7. Vai para layers_historico/incerteza.json.
# ============================================================
import json, statistics

def pct_veg(img):
    return 100 * img.gte(0.25).rename('ndvi').reduceRegion(
        ee.Reducer.mean(), portoMuniGeom, 30, maxPixels=1e9).get('ndvi').getInfo()

def _ep(vals):
    return statistics.stdev(vals) / len(vals) ** 0.5 if len(vals) > 1 else None

print('\nA medir a dispersao ano a ano por epoca...')
incerteza = {}
for name, sensor, years in EPOCHS:
    vals = []
    for y in years:
        im, cnt = get_ndvi_composite(sensor, [y])
        if sensor == 'Landsat 8':
            im = im.subtract(OFFSET_OLI)
        vals.append(pct_veg(im))
    incerteza[name] = {'anos': years, 'veg_por_ano': [round(v, 1) for v in vals],
                       'media_anos': round(statistics.mean(vals), 1),
                       'dp_anual': round(statistics.stdev(vals), 1),
                       'ep': round(_ep(vals), 1)}
    print(f'  {name}: media dos anos {incerteza[name]["media_anos"]}  dp {incerteza[name]["dp_anual"]}  ep {incerteza[name]["ep"]}')

dif_ponte = []
for y in PONTE_ANOS:
    dif_ponte.append(pct_veg(composito_l8_so([y])) - pct_veg(composito_l7([y])))
incerteza['ponte_L8_L7'] = {'anos': PONTE_ANOS, 'dif_pp_por_ano': [round(v, 1) for v in dif_ponte],
                            'media_pp': round(statistics.mean(dif_ponte), 1), 'ep': round(_ep(dif_ponte), 1)}
print(f'  ponte L8-L7 (bruta, p.p.): {incerteza["ponte_L8_L7"]}')
os.makedirs(LAYERS_DIR, exist_ok=True)
with open(os.path.join(LAYERS_DIR, 'incerteza.json'), 'w', encoding='utf-8') as _f:
    json.dump(incerteza, _f, ensure_ascii=False, indent=1)


# ============================================================
# Download das camadas
# ============================================================
os.makedirs(LAYERS_DIR, exist_ok=True)
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
            url = vis_image.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png', 'crs': 'EPSG:4326'})
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
    return _robust_download(vis, os.path.join(LAYERS_DIR, filename), label)

def download_mask(image, color_hex, filename):
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    return _robust_download(vis, os.path.join(LAYERS_DIR, filename), filename, transparent_black=True)

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
# Com histerese (2026-11-18; a versao simples 1985-90 vs 2023-24 era sobretudo ruido do limiar: 54 % da
# perda em manchas <1 ha): mudanca de classe nas duas epocas de cada ponta E salto de NDVI >= 0,15 E mancha
# >= 0,5 ha (6 pixeis ligados).
DELTA_NDVI = 0.15
MANCHA_MIN_PX = 6
_a1, _a2 = EPOCHS[0][0], EPOCHS[1][0]      # 1985-90, 1995-00
_b1, _b2 = EPOCHS[-2][0], EPOCHS[-1][0]    # 2016-17, 2023-24

MANCHA_MIN_HA = 0.5

def filtrar_manchas(png, min_ha=MANCHA_MIN_HA):
    """Tira ao PNG de perda/ganho as manchas (8-ligadas, dentro do concelho) com menos de min_ha.
    Feito em Python depois do download: o connectedPixelCount do GEE reavalia-se a escala do render
    (6,6 m) e deixava 298 de 339 manchas abaixo de 0,5 ha."""
    import numpy as np
    from scipy import ndimage as ndi
    im = Image.open(png).convert('RGBA')
    arr = np.array(im)
    concelho = np.array(Image.open(os.path.join(LAYERS_DIR, 'porto_mask.png')))[..., 3] > 0
    ha_px = 4142.1 / concelho.sum()
    dentro = (arr[..., 3] > 0) & concelho
    lab, k = ndi.label(dentro, np.ones((3, 3)))
    area = np.bincount(lab.ravel(), minlength=k + 1) * ha_px
    manter = area >= min_ha
    manter[0] = False
    arr[dentro & ~manter[lab]] = (0, 0, 0, 0)   # fora do concelho nao se mexe (so cor)
    Image.fromarray(arr).save(png)
    return float(area[manter].sum()), int(manter.sum())

def _mancha(m):
    return m.selfMask()

_nv = {n: veg_masks[n].Not() for n in veg_masks}
_loss = (veg_masks[_a1].And(veg_masks[_a2]).And(_nv[_b1]).And(_nv[_b2])
         .And(composites[first_epoch].subtract(composites[last_epoch]).gte(DELTA_NDVI)))
_gain = (_nv[_a1].And(_nv[_a2]).And(veg_masks[_b1]).And(veg_masks[_b2])
         .And(composites[last_epoch].subtract(composites[first_epoch]).gte(DELTA_NDVI)))
veg_loss = _mancha(_loss)
veg_gain = _mancha(_gain)

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
for _m, _cor, _f in ((veg_loss, 'FF4444', 'veg_perda.png'), (veg_gain, '44FF44', 'veg_ganho.png')):
    download_mask(_m, _cor, _f)
    _ha, _n = filtrar_manchas(os.path.join(LAYERS_DIR, _f))
    print(f'  {_f}: {_n} manchas >= {MANCHA_MIN_HA} ha, {_ha:.1f} ha no concelho')
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
    reducer=ee.Reducer.sum(), geometry=portoMuniGeom, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)

for name, sensor, years in EPOCHS:
    stats = composites[name].reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=portoMuniGeom,
        scale=30,
        maxPixels=1e9
    ).getInfo()
    veg_count = veg_masks[name].reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=portoMuniGeom,
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
    reducer=ee.Reducer.sum(), geometry=portoMuniGeom, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)
gain_count = veg_gain.unmask(0).reduceRegion(
    reducer=ee.Reducer.sum(), geometry=portoMuniGeom, scale=30, maxPixels=1e9
).getInfo().get('ndvi', 0)
print('\n  (perda/ganho com histerese, ANTES do filtro de manchas >= 0,5 ha; os valores finais estao acima)')
print(f'  Vegetacao perdida ({first_epoch} -> {last_epoch}): {loss_count * PIXEL_AREA_HA:.0f} ha')
print(f'  Vegetacao ganha  ({first_epoch} -> {last_epoch}): {gain_count * PIXEL_AREA_HA:.0f} ha')
print(f'  Balanco liquido: {(gain_count - loss_count) * PIXEL_AREA_HA:+.0f} ha')


# build_html retirado em 2026-11-18: ndvi_historico.html é agora um redireccionamento para o mapa único
# (e a chamada falhava à procura de 1947/layers). As camadas vão para layers_historico/ e o mapa lê-as.
