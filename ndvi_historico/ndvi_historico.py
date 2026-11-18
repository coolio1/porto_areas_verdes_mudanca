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
print(f'  % vegetacao na sobreposicao (so diagnostico, limiar 0,25): L7={_pct(_l7):.1f}  L8 bruto={_pct(_l8):.1f}  '
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
# Fraccao de vegetacao por pixel (fase 2, 2026-11-18)
# ============================================================
# O limiar fixo NDVI >= 0,25 a 30 m sobrestima a vegetacao urbana (27-36 % do construido de 1979 contava como
# vegetacao) e mistura perda real com pixeis mistos. Aqui o NDVI converte-se numa FRACCAO de vegetacao por pixel
# com uma curva empirica monotona NDVI -> fraccao, calibrada em 2023-24 contra a classificacao Sentinel-2 (10 m)
# do tema «Hoje» (Arvores + Solo = nao edificado, layers/uso_*.png). A mesma curva aplica-se a todas as epocas
# (os sensores ja estao ligados pela ponte L7). Guarda layers_historico/fvc_calibracao.json.
import json
import statistics
import numpy as np
import rasterio
from scipy import ndimage as ndi

GRELHA_W, GRELHA_H = 2048, 769   # grelha das camadas (EPSG:4326, caixa `porto`)

def baixar_matriz(img, tentativas=5):
    """Descarrega uma imagem EE (1 banda) como matriz float na grelha das camadas (nan onde sem dados)."""
    for t in range(tentativas):
        try:
            url = img.getDownloadURL({'region': porto, 'dimensions': f'{GRELHA_W}x{GRELHA_H}',
                                      'crs': 'EPSG:4326', 'format': 'GEO_TIFF'})
            dados = requests.get(url, timeout=300).content
            with rasterio.open(io.BytesIO(dados)) as ds:
                a = ds.read(1).astype(np.float32)
                if ds.nodata is not None:
                    a[a == ds.nodata] = np.nan
            return a
        except Exception as e:
            print(f'  descarga da matriz falhou ({t + 1}/{tentativas}): {str(e)[:80]}')
            time.sleep(5 * (t + 1))
    raise RuntimeError('nao foi possivel descarregar a matriz')

def _alfa(caminho):
    return np.array(Image.open(caminho))[..., 3]

def _isotonica(y, w):
    """Regressao isotonica crescente (PAVA) com pesos."""
    blocos = []
    for yi, wi in zip(y, w):
        blocos.append([yi, wi, 1])
        while len(blocos) > 1 and blocos[-2][0] > blocos[-1][0]:
            b2, b1 = blocos.pop(), blocos.pop()
            wt = b1[1] + b2[1]
            blocos.append([(b1[0] * b1[1] + b2[0] * b2[1]) / wt, wt, b1[2] + b2[2]])
    return np.concatenate([[b[0]] * b[2] for b in blocos])

print('\nA calibrar NDVI -> fraccao de vegetacao (2023-24 vs Sentinel-2 do tema Hoje)...')
CONCELHO = _alfa(os.path.join(LAYERS_DIR, 'porto_mask.png')) > 0
_ref = (_alfa(os.path.join(ROOT_DIR, 'layers', 'uso_arvores.png')) > 0) | \
       (_alfa(os.path.join(ROOT_DIR, 'layers', 'uso_solo.png')) > 0)
_n23 = baixar_matriz(composites['2023-24'])
_ok = CONCELHO & np.isfinite(_n23)
_bordas = np.arange(-0.2, 0.9001, 0.025)
_idx = np.digitize(_n23[_ok], _bordas) - 1
_xs, _ys, _ws = [], [], []
for _i in range(len(_bordas) - 1):
    _s = _idx == _i
    if _s.sum() >= 300:
        _xs.append(float(_n23[_ok][_s].mean())); _ys.append(float(_ref[_ok][_s].mean())); _ws.append(int(_s.sum()))
_ys = np.clip(_isotonica(_ys, _ws), 0, 1)
LUT_X = [round(x, 4) for x in _xs]
LUT_Y = [round(float(y), 4) for y in _ys]
_fvc23 = np.interp(_n23[_ok], LUT_X, LUT_Y)
print(f'  referencia (Arvores+Solo, Hoje): {100 * _ref[_ok].mean():.1f} %  | fraccao calibrada 2023-24: {100 * _fvc23.mean():.1f} %')
with open(os.path.join(LAYERS_DIR, 'fvc_calibracao.json'), 'w', encoding='utf-8') as _f:
    json.dump({'ndvi': LUT_X, 'fraccao': LUT_Y, 'pixeis': int(_ok.sum()),
               'ref_pct': round(100 * float(_ref[_ok].mean()), 1), 'fvc_2023_24_pct': round(100 * float(_fvc23.mean()), 1),
               'referencia': 'layers/uso_arvores.png + uso_solo.png (Sentinel-2 10 m, tema Hoje)'},
              _f, indent=1)

def fvc(ndvi_img):
    """NDVI (bandas 'ndvi') -> fraccao de vegetacao 0-1, pela curva calibrada."""
    return ndvi_img.interpolate(LUT_X, LUT_Y, 'clamp').rename('ndvi')

# ============================================================
# Incerteza por epoca: dispersao ano a ano da % de vegetacao (fraccao media no concelho, 1 compósito por ano)
# e erro residual da ponte L8-L7 (depois do desvio). Vai para layers_historico/incerteza.json.
# ============================================================
def pct_veg(ndvi_img):
    return 100 * fvc(ndvi_img).reduceRegion(
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
    dif_ponte.append(pct_veg(composito_l8_so([y]).subtract(OFFSET_OLI)) - pct_veg(composito_l7([y])))
incerteza['ponte_L8_L7'] = {'anos': PONTE_ANOS, 'dif_pp_por_ano': [round(v, 1) for v in dif_ponte],
                            'media_pp': round(statistics.mean(dif_ponte), 1), 'ep': round(_ep(dif_ponte), 1)}
print(f'  ponte L8-L7 (residual apos o desvio, p.p.): {incerteza["ponte_L8_L7"]}')
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
# Camadas de vegetacao, edificado e perda/ganho (calculadas em Python a partir da fraccao por pixel)
# ============================================================
# veg_<epoca>.png : alfa = fraccao de vegetacao (0-255); a cor e so tingida no mapa. Fora do concelho mantem-se
#                   (so cor); os numeros contam apenas dentro do concelho (mapa_unico/historico_numeros.py).
# edif_<epoca>.png: alfa = (1 - fraccao) onde nao ha agua permanente (JRC GSW > 50 %), so dentro do concelho.
# veg_perda/ganho : variacao da fraccao entre o inicio (media 1985-90 e 1995-00) e o fim (2016-17 e 2023-24)
#                   >= DELTA_FVC, em manchas >= MANCHA_MIN_HA dentro do concelho (histerese: sem 1 so epoca).
DELTA_FVC = 0.30
MANCHA_MIN_HA = 0.5
first_epoch = EPOCHS[0][0]   # 1985-90
last_epoch = EPOCHS[-1][0]   # 2023-24
_inicio = [EPOCHS[0][0], EPOCHS[1][0]]      # 1985-90, 1995-00
_fim = [EPOCHS[-2][0], EPOCHS[-1][0]]       # 2016-17, 2023-24
HA_PX = 4142.1 / CONCELHO.sum()             # ha por pixel da grelha (CAOP 2025)

NIVEIS_ALFA = 16   # alfa quantizado a 16 niveis (a fraccao tem ~5 p.p. de erro): PNG e historico.js ficam leves

def alfa_de(fraccao):
    """Fraccao 0-1 -> alfa uint8 quantizado a NIVEIS_ALFA niveis (multiplos de 255/(N-1))."""
    return np.round(np.round(np.clip(fraccao, 0, 1) * (NIVEIS_ALFA - 1)) * 255 / (NIVEIS_ALFA - 1)).astype(np.uint8)

def png_alfa(alfa, cor_hex, caminho):
    """Grava RGBA com cor fixa e o alfa dado (uint8)."""
    r, g, b = (int(cor_hex[i:i + 2], 16) for i in (0, 2, 4))
    rgba = np.zeros(alfa.shape + (4,), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3] = r, g, b, alfa
    Image.fromarray(rgba).save(caminho)

def manchas_minimas(bool_arr, min_ha=MANCHA_MIN_HA):
    """Mantem so as manchas (8-ligadas) dentro do concelho com area >= min_ha; fora do concelho nao se mexe."""
    dentro = bool_arr & CONCELHO
    lab, k = ndi.label(dentro, np.ones((3, 3)))
    area = np.bincount(lab.ravel(), minlength=k + 1) * HA_PX
    manter = area >= min_ha
    manter[0] = False
    out = bool_arr & (~CONCELHO | manter[lab])
    return out, float(area[manter].sum()), int(manter.sum())

print('\nA descarregar a agua permanente (JRC) e a fraccao de vegetacao por epoca...')
jrc_water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater').select('occurrence')
water_mask = jrc_water.unmask(0).gt(50).clip(porto).rename('ndvi')
AGUA = np.nan_to_num(baixar_matriz(water_mask)) > 0.5

FVC = {}
for name, sensor, years in EPOCHS:
    a = baixar_matriz(fvc(composites[name]))
    FVC[name] = np.clip(np.nan_to_num(a, nan=0.0), 0, 1)
    alfa_v = alfa_de(FVC[name])
    png_alfa(alfa_v, '00FF00', os.path.join(LAYERS_DIR, f'veg_{name}.png'))
    alfa_e = alfa_de(1 - FVC[name])
    alfa_e[~CONCELHO | AGUA] = 0
    png_alfa(alfa_e, 'C4A882', os.path.join(LAYERS_DIR, f'edif_{name}.png'))
    print(f'  {name}: veg {100 * (alfa_v[CONCELHO] / 255).mean():.1f} %  edif {100 * (alfa_e[CONCELHO] / 255).mean():.1f} %')

_ini = np.mean([FVC[n] for n in _inicio], axis=0)
_fi = np.mean([FVC[n] for n in _fim], axis=0)
for _f, _delta, _cor in (('veg_perda.png', _ini - _fi, 'FF4444'), ('veg_ganho.png', _fi - _ini, '44FF44')):
    _m, _ha, _n = manchas_minimas(_delta >= DELTA_FVC)
    png_alfa(np.where(_m, 255, 0).astype(np.uint8), _cor, os.path.join(LAYERS_DIR, _f))
    print(f'  {_f}: {_n} manchas >= {MANCHA_MIN_HA} ha, {_ha:.1f} ha no concelho')

# NDVI por epoca (so visual)
DOWNLOAD_PAUSE = 5  # segundos entre downloads
print('\nA descarregar camadas NDVI...')
for name, sensor, years in EPOCHS:
    download_ndvi(composites[name], f'ndvi_{name}.png', f'NDVI {name}')
    time.sleep(DOWNLOAD_PAUSE)

# Municipios
print('\nA descarregar limites...')
muni_styled = ee.Image().byte().paint(featureCollection=municipiosPorto, color=1, width=2)
download_mask(muni_styled, 'FFFFFF', 'municipios.png')

# ============================================================
# Estatisticas (a partir das camadas gravadas, dentro do concelho)
# ============================================================
print('\n--- Estatisticas por epoca (fraccao de vegetacao, % do concelho) ---')
for name, sensor, years in EPOCHS:
    v = FVC[name][CONCELHO].mean()
    print(f'  {name:<10} veg {100 * v:5.1f} %  = {4142.1 * v:6.0f} ha-equivalentes')

# build_html retirado em 2026-11-18: ndvi_historico.html é agora um redireccionamento para o mapa único
# (e a chamada falhava à procura de 1947/layers). As camadas vão para layers_historico/ e o mapa lê-as.


# build_html retirado em 2026-11-18: ndvi_historico.html é agora um redireccionamento para o mapa único
# (e a chamada falhava à procura de 1947/layers). As camadas vão para layers_historico/ e o mapa lê-as.
