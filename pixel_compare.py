"""Comparar espectro de dois pixeis: relva vs arvores."""
import ee
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Pontos fornecidos pelo utilizador
relva = ee.Geometry.Point([-8.616731, 41.188319])   # 41°11'17.95"N 8°37'00.23"W
arvore = ee.Geometry.Point([-8.619431, 41.189633])   # 41°11'22.68"N 8°37'09.95"W

ALL_BANDS = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12', 'SCL']

s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(relva.buffer(100))
    .filterDate('2024-05-01', '2025-10-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
    .select(ALL_BANDS))

def process(img):
    scl = img.select('SCL')
    clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2))
    return img.updateMask(clear)

s2_clean = s2.map(process)
composite = s2_clean.median()

# Extrair valores de todas as bandas para cada ponto
print('=== VALORES ESPECTRAIS (mediana verao 2024-25) ===\n')

bands_to_show = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12']
band_names = {
    'B2': 'Blue (490nm)',
    'B3': 'Green (560nm)',
    'B4': 'Red (665nm)',
    'B5': 'RedEdge1 (705nm)',
    'B6': 'RedEdge2 (740nm)',
    'B7': 'RedEdge3 (783nm)',
    'B8': 'NIR (842nm)',
    'B8A': 'NIR narrow (865nm)',
    'B11': 'SWIR1 (1610nm)',
    'B12': 'SWIR2 (2190nm)',
}

vals_relva = composite.select(bands_to_show).reduceRegion(
    reducer=ee.Reducer.first(), geometry=relva, scale=10
).getInfo()

vals_arvore = composite.select(bands_to_show).reduceRegion(
    reducer=ee.Reducer.first(), geometry=arvore, scale=10
).getInfo()

print(f'{"Banda":<25} {"Relva":>8} {"Arvore":>8} {"Ratio R/A":>10} {"Diff":>8}')
print('-' * 65)
for b in bands_to_show:
    vr = vals_relva.get(b)
    va = vals_arvore.get(b)
    if vr is not None and va is not None:
        ratio = vr / va if va > 0 else 0
        diff = vr - va
        print(f'{band_names[b]:<25} {vr:>8.1f} {va:>8.1f} {ratio:>10.2f} {diff:>+8.1f}')

# Indices derivados
print('\n=== INDICES DERIVADOS ===\n')

def calc_indices(vals):
    b3 = vals['B3']
    b4 = vals['B4']
    b5 = vals['B5']
    b6 = vals['B6']
    b7 = vals['B7']
    b8 = vals['B8']
    b8a = vals.get('B8A', b8)
    b11 = vals['B11']
    b12 = vals['B12']

    ndvi = (b8 - b4) / (b8 + b4) if (b8 + b4) > 0 else 0
    ndmi = (b8 - b11) / (b8 + b11) if (b8 + b11) > 0 else 0
    ndre = (b8 - b5) / (b8 + b5) if (b8 + b5) > 0 else 0
    nir_green = b8 / max(b3, 1)
    re_ratio = b6 / max(b5, 1)

    # Indices adicionais que podem ajudar
    ndre2 = (b7 - b5) / (b7 + b5) if (b7 + b5) > 0 else 0  # Red Edge NDI com B7
    cri = (1/max(b3, 1)) - (1/max(b5, 1))  # Carotenoid Reflectance Index
    repi = b5 + (b6 - b5) * ((b4 + b7) / 2 - b5) / max(b6 - b5, 1)  # Red Edge Position
    b8a_b8 = b8a / max(b8, 1)  # NIR narrow vs broad
    swir_ratio = b11 / max(b12, 1)  # SWIR ratio (estrutura canopia)
    ndvi_re = (b7 - b4) / (b7 + b4) if (b7 + b4) > 0 else 0  # NDVI com RedEdge3
    green_red = b3 / max(b4, 1)  # Green/Red ratio
    evi = 2.5 * (b8 - b4) / max(b8 + 6*b4 - 7.5*b3 + 1, 1)  # EVI

    return {
        'NDVI': ndvi, 'NDMI': ndmi, 'NDRE (B8-B5)': ndre,
        'NIR/Green': nir_green, 'RE ratio (B6/B5)': re_ratio,
        'NDRE2 (B7-B5)': ndre2, 'CRI (1/B3-1/B5)': cri,
        'B8A/B8': b8a_b8, 'SWIR ratio (B11/B12)': swir_ratio,
        'NDVI_RE (B7-B4)': ndvi_re, 'Green/Red (B3/B4)': green_red,
        'EVI': evi, 'B3 (raw)': b3,
    }

idx_relva = calc_indices(vals_relva)
idx_arvore = calc_indices(vals_arvore)

print(f'{"Indice":<25} {"Relva":>8} {"Arvore":>8} {"Diff":>8} {"Separa?":>8}')
print('-' * 60)
for name in idx_relva:
    vr = idx_relva[name]
    va = idx_arvore[name]
    diff = abs(vr - va)
    # Marcar como bom separador se diferenca > 20% do range
    avg = (abs(vr) + abs(va)) / 2
    separa = 'SIM' if avg > 0 and diff / avg > 0.3 else ''
    print(f'{name:<25} {vr:>8.4f} {va:>8.4f} {vr-va:>+8.4f} {separa:>8}')

# Tambem ver variabilidade temporal - talvez haja uma epoca do ano melhor
print('\n=== VARIABILIDADE TEMPORAL (cenas individuais) ===\n')
n_scenes = s2_clean.size().getInfo()
print(f'Total cenas limpas: {n_scenes}')

# Extrair NDVI e NDRE de cada cena para os dois pontos
def extract_ts(img):
    date = img.date().format('YYYY-MM-dd')
    ndvi_r = img.normalizedDifference(['B8', 'B4']).reduceRegion(
        ee.Reducer.first(), relva, 10).get('nd')
    ndvi_a = img.normalizedDifference(['B8', 'B4']).reduceRegion(
        ee.Reducer.first(), arvore, 10).get('nd')
    ndre_r = img.normalizedDifference(['B8', 'B5']).reduceRegion(
        ee.Reducer.first(), relva, 10).get('nd')
    ndre_a = img.normalizedDifference(['B8', 'B5']).reduceRegion(
        ee.Reducer.first(), arvore, 10).get('nd')
    b3_r = img.select('B3').reduceRegion(
        ee.Reducer.first(), relva, 10).get('B3')
    b3_a = img.select('B3').reduceRegion(
        ee.Reducer.first(), arvore, 10).get('B3')
    return ee.Feature(None, {
        'date': date,
        'ndvi_relva': ndvi_r, 'ndvi_arvore': ndvi_a,
        'ndre_relva': ndre_r, 'ndre_arvore': ndre_a,
        'b3_relva': b3_r, 'b3_arvore': b3_a,
    })

ts = s2_clean.map(extract_ts).getInfo()

print(f'\n{"Data":<12} {"NDVI_R":>7} {"NDVI_A":>7} {"dNDVI":>7} {"NDRE_R":>7} {"NDRE_A":>7} {"dNDRE":>7} {"B3_R":>6} {"B3_A":>6}')
print('-' * 80)
for f in sorted(ts['features'], key=lambda x: x['properties']['date']):
    p = f['properties']
    if p['ndvi_relva'] is None or p['ndvi_arvore'] is None:
        continue
    d = p['date']
    nr, na = p['ndvi_relva'], p['ndvi_arvore']
    dr, da = p['ndre_relva'], p['ndre_arvore']
    b3r, b3a = p['b3_relva'] or 0, p['b3_arvore'] or 0
    print(f'{d:<12} {nr:>7.3f} {na:>7.3f} {nr-na:>+7.3f} {dr:>7.3f} {da:>7.3f} {dr-da:>+7.3f} {b3r:>6.0f} {b3a:>6.0f}')

print('\nDone.')
