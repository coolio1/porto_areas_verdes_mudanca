"""Estatisticas de uso do solo e transicoes para o Porto."""
import ee
import os

GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])

municipios = ee.FeatureCollection(f'projects/{GEE_PROJECT}/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
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
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])
    for year in years:
        all_col = all_col.merge(getS2col(f'{year}-05-01', f'{year}-10-31'))
        spring_col = spring_col.merge(getS2col(f'{year}-05-15', f'{year}-06-30'))
    median = all_col.median().clip(porto)
    spring_ndvi = spring_col.select('ndvi').reduce(
        ee.Reducer.percentile([15])).rename('spring_ndvi').clip(porto)
    ndvi_min = all_col.select('ndvi').reduce(
        ee.Reducer.percentile([10])).rename('ndvi_min').clip(porto)
    return median.addBands(spring_ndvi).addBands(ndvi_min)

print('A calcular compositos...')
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

esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(porto)
esaBuilt = esa.eq(50)

def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min):
    b3_ok = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isTreeStrict = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok)
    )
    b3_ok_mixed = green.lt(600).Or(green.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTreeStrict.Not())
    )
    isTree = isTreeStrict.Or(isMixed)
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isTreeStrict, isMixed, isBuilt, isSolo

print('A classificar...')
isTree_e, isTreeStrict_e, isMixed_e, isBuilt_e, isSolo_e = classify(
    ndvi_e, ndbi_e, nirgreen_e, green_e, spring_ndvi_e, ndvi_min_e)
isTree_l_base, isTreeStrict_l, isMixed_l, isBuilt_l_base, _ = classify(
    ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l)

stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isSolo_l = isTree_l.Not().And(isBuilt_l.Not())

ndviDrop = ndvi_e.subtract(ndvi_l)
treesToSolo  = isTree_e.And(isSolo_l).And(ndviDrop.gte(0.15))
treesToBuilt = isTree_e.And(isBuilt_l).And(ndviDrop.gte(0.15))
soloToBuilt  = isSolo_e.And(isBuilt_l).And(ndviDrop.gte(0.1))
soloToTrees  = isTree_e.Not().And(isTree_l).And(ndvi_l.subtract(ndvi_e).gte(0.15))

pixel_area = ee.Image.pixelArea()

def calc_ha(mask, geometry):
    area_m2 = mask.multiply(pixel_area).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=geometry, scale=10, maxPixels=1e9
    ).getInfo()
    key = list(area_m2.keys())[0]
    return area_m2[key] / 10000 if area_m2[key] else 0

# === ESTATISTICAS TOTAIS ===
print('\n' + '='*60)
print('ESTATISTICAS DO PORTO')
print('='*60)

print('\n--- Uso do solo (ha) ---')
classes = [
    ('Arvores', isTree_e, isTree_l),
    ('  - Arvores puras', isTreeStrict_e, isTreeStrict_l.And(isBuilt_l.Not())),
    ('  - Verde urbano', isMixed_e, isMixed_l.And(isBuilt_l.Not())),
    ('Solo/Relva', isSolo_e, isSolo_l),
    ('Edificado', isBuilt_e, isBuilt_l),
]

print(f'\n{"Classe":<20} {"2016-17":>10} {"2024-25":>10} {"Mudanca":>10} {"Mudanca%":>10}')
print('-' * 62)
for name, mask_e, mask_l in classes:
    ha_e = calc_ha(mask_e.selfMask(), porto)
    ha_l = calc_ha(mask_l.selfMask(), porto)
    diff = ha_l - ha_e
    pct = (diff / ha_e * 100) if ha_e > 0 else 0
    print(f'{name:<20} {ha_e:>10.1f} {ha_l:>10.1f} {diff:>+10.1f} {pct:>+9.1f}%')

print('\n--- Transicoes (ha) ---')
transitions = [
    ('Arvores -> Edificado', treesToBuilt),
    ('Arvores -> Solo', treesToSolo),
    ('Solo -> Edificado', soloToBuilt),
    ('Solo -> Arvores', soloToTrees),
]

for name, mask in transitions:
    ha = calc_ha(mask.selfMask(), porto)
    print(f'  {name}: {ha:.1f} ha')

print('\nDone.')
