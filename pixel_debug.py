"""Comparar pixel de relva vs outros pixels do cluster verde urbano."""
import ee
import os

GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# Pixel de relva/solo no cluster verde urbano
relva = ee.Geometry.Point([-8.617444, 41.190000])  # 41°11'24.00"N 8°37'03.88"W

# Pontos que devem ser verde urbano verdadeiro (arvores mistas)
# Vou amostrar varios pontos do cluster para comparar
LAT, LON = 41.188117, -8.617633
BUFFER = 1500
point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(area).filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(BANDS))
    def process(img):
        scl = img.select('SCL')
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi = img.normalizedDifference(['B11', 'B8']).rename('ndbi')
        ndmi = img.normalizedDifference(['B8', 'B11']).rename('ndmi')
        nir_green = img.select('B8').divide(img.select('B3').max(1)).rename('nir_green')
        b3 = img.select('B3').rename('b3')
        return ndvi.addBands(ndbi).addBands(ndmi).addBands(nir_green).addBands(b3).updateMask(clear)
    return s2.map(process)

# Compositos
print('A calcular compositos...')
years = [2024, 2025]
all_col = ee.ImageCollection([])
spring_col = ee.ImageCollection([])
for year in years:
    full = getS2col(f'{year}-05-01', f'{year}-10-31')
    all_col = all_col.merge(full)
    spring = getS2col(f'{year}-05-15', f'{year}-06-30')
    spring_col = spring_col.merge(spring)

median = all_col.median().clip(area)
spring_ndvi = spring_col.select('ndvi').reduce(ee.Reducer.percentile([15])).rename('spring_ndvi').clip(area)
ndvi_min = all_col.select('ndvi').reduce(ee.Reducer.percentile([10])).rename('ndvi_min').clip(area)
composite = median.addBands(spring_ndvi).addBands(ndvi_min)

# Classificar para encontrar pixels verde urbano
ndvi = median.select('ndvi')
ndbi = median.select('ndbi')
nirgreen = median.select('nir_green')
b3 = median.select('b3')

esaBuilt = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(area).eq(50)

isTree = (ndvi.gte(0.5)
    .And(spring_ndvi.gte(0.7))
    .And(ndvi_min.gte(0.3))
    .And(nirgreen.gte(4))
    .And(b3.lt(600))
)
isMixed = (ndvi.gte(0.5)
    .And(spring_ndvi.gte(0.5))
    .And(ndvi_min.gte(0.2))
    .And(isTree.Not())
)

# Valores do pixel de relva
print('\n=== PIXEL DE RELVA (41.190N, 8.617W) ===')
all_bands = ['ndvi', 'ndbi', 'ndmi', 'nir_green', 'b3', 'spring_ndvi', 'ndvi_min']
vals = composite.select(all_bands).reduceRegion(
    reducer=ee.Reducer.first(), geometry=relva, scale=10
).getInfo()
for k, v in sorted(vals.items()):
    print(f'  {k}: {v:.4f}' if v is not None else f'  {k}: None')

# Estatisticas do cluster verde urbano inteiro
print('\n=== CLUSTER VERDE URBANO - ESTATISTICAS ===')
mixed_composite = composite.select(all_bands).updateMask(isMixed)
stats = mixed_composite.reduceRegion(
    reducer=ee.Reducer.percentile([10, 25, 50, 75, 90]),
    geometry=area, scale=10, maxPixels=1e8
).getInfo()

for band in all_bands:
    vals_b = []
    for p in [10, 25, 50, 75, 90]:
        key = f'{band}_p{p}'
        v = stats.get(key)
        vals_b.append(f'p{p}={v:.3f}' if v is not None else f'p{p}=None')
    print(f'  {band}: {", ".join(vals_b)}')

# Serie temporal do pixel de relva
print('\n=== SERIE TEMPORAL - PIXEL RELVA ===')
def extract_ts(img):
    date = img.date().format('YYYY-MM-dd')
    ndvi_v = img.select('ndvi').reduceRegion(ee.Reducer.first(), relva, 10).get('ndvi')
    nirg_v = img.select('nir_green').reduceRegion(ee.Reducer.first(), relva, 10).get('nir_green')
    b3_v = img.select('b3').reduceRegion(ee.Reducer.first(), relva, 10).get('b3')
    return ee.Feature(None, {'date': date, 'ndvi': ndvi_v, 'nirgreen': nirg_v, 'b3': b3_v})

ts = all_col.map(extract_ts).getInfo()
print(f'{"Data":<12} {"NDVI":>7} {"NIR/G":>7} {"B3":>6}')
print('-' * 35)
for f in sorted(ts['features'], key=lambda x: x['properties']['date']):
    p = f['properties']
    if p['ndvi'] is None:
        continue
    print(f'{p["date"]:<12} {p["ndvi"]:>7.3f} {p["nirgreen"]:>7.2f} {p["b3"]:>6.0f}')

# Onde esta o pixel na classificacao?
is_tree_val = isTree.reduceRegion(ee.Reducer.first(), relva, 10).getInfo()
is_mixed_val = isMixed.reduceRegion(ee.Reducer.first(), relva, 10).getInfo()
print(f'\nPixel classificado como:')
print(f'  isTree: {is_tree_val}')
print(f'  isMixed: {is_mixed_val}')

# Qual filtro falhou para nao ser arvore?
print('\n=== QUAL FILTRO FALHOU? ===')
v = composite.select(all_bands).reduceRegion(
    reducer=ee.Reducer.first(), geometry=relva, scale=10
).getInfo()
ndvi_v = v['ndvi']
spring_v = v['spring_ndvi']
min_v = v['ndvi_min']
nirg_v = v['nir_green']
b3_v = v['b3']

print(f'  NDVI >= 0.5: {ndvi_v:.3f} {"PASS" if ndvi_v >= 0.5 else "FAIL"}')
print(f'  Spring >= 0.7: {spring_v:.3f} {"PASS" if spring_v >= 0.7 else "FAIL"}')
print(f'  Min >= 0.3: {min_v:.3f} {"PASS" if min_v >= 0.3 else "FAIL"}')
print(f'  NIR/Green >= 4: {nirg_v:.3f} {"PASS" if nirg_v >= 4 else "FAIL"}')
print(f'  B3 < 600: {b3_v:.3f} {"PASS" if b3_v < 600 else "FAIL"}')

# E qual filtro do verde urbano passou?
print(f'\n  NDVI >= 0.5: {ndvi_v:.3f} {"PASS" if ndvi_v >= 0.5 else "FAIL"}')
print(f'  Spring >= 0.5: {spring_v:.3f} {"PASS" if spring_v >= 0.5 else "FAIL"}')
print(f'  Min >= 0.2: {min_v:.3f} {"PASS" if min_v >= 0.2 else "FAIL"}')

print('\nDone.')
