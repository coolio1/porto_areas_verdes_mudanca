"""Cluster analysis - encontrar numero ideal de clusters."""
import ee
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

LAT, LON = 41.188117, -8.617633
BUFFER = 1500

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

BANDS = ['B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11', 'SCL']

def getS2(start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(area).filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(BANDS))
    def process(img):
        scl = img.select('SCL')
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndmi = img.normalizedDifference(['B8', 'B11']).rename('ndmi')
        nir_green = img.select('B8').divide(img.select('B3').max(1)).rename('nir_green')
        b3 = img.select('B3').rename('b3')
        # Red Edge indices
        ndre = img.normalizedDifference(['B8', 'B5']).rename('ndre')
        re_ratio = img.select('B6').divide(img.select('B5').max(1)).rename('re_ratio')
        return (ndvi.addBands(ndmi).addBands(nir_green).addBands(b3)
                .addBands(ndre).addBands(re_ratio).updateMask(clear))
    return s2.map(process).median().clip(area)

print('A calcular composito recente...')
s2 = getS2('2024-01-01', '2026-03-20')

features = ['ndvi', 'ndmi', 'nir_green', 'b3', 'ndre', 're_ratio']
composite = s2.select(features)

# Amostrar pixels para clustering
print('A amostrar pixels...')
training = composite.sample(
    region=area, scale=10, numPixels=5000, seed=42
)

# --- Testar k=2 ate k=10 usando WCSS (Within-Cluster Sum of Squares) ---
print('\n--- Elbow method: WCSS para k=2..10 ---')
pixel_area_img = ee.Image.pixelArea()
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(area)
esa_classes = {10: 'Tree', 20: 'Shrub', 30: 'Grass', 40: 'Crop', 50: 'Built', 60: 'Bare', 80: 'Water'}

for k in range(2, 11):
    clusterer = ee.Clusterer.wekaKMeans(k).train(training)
    clustered = composite.cluster(clusterer).rename('cluster')

    # WCSS: distancia de cada pixel ao centroide do seu cluster
    # Calcular variancia intra-cluster como proxy
    total_var = 0
    for c in range(k):
        mask = clustered.eq(c)
        # Variancia de cada feature dentro do cluster
        var_stats = composite.updateMask(mask).reduceRegion(
            reducer=ee.Reducer.variance(), geometry=area, scale=10, maxPixels=1e8
        ).getInfo()
        # Area do cluster para pesar
        area_stats = mask.multiply(pixel_area_img).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
        ).getInfo()
        cluster_ha = area_stats['cluster'] / 10000 if area_stats.get('cluster') else 0
        cluster_var = sum(v for v in var_stats.values() if v is not None)
        total_var += cluster_var * cluster_ha

    print(f'  k={k:2d}: WCSS={total_var:.2f}')

# --- Detalhe para o k otimo (vamos mostrar k=4,5,6 para comparar) ---
for k in [4, 5, 6]:
    print(f'\n{"="*60}')
    print(f'=== DETALHE k={k} ===')
    print(f'{"="*60}')

    clusterer = ee.Clusterer.wekaKMeans(k).train(training)
    clustered = composite.cluster(clusterer).rename('cluster')

    for c in range(k):
        mask = clustered.eq(c)
        area_stats = mask.multiply(pixel_area_img).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
        ).getInfo()
        ha = area_stats['cluster'] / 10000 if area_stats.get('cluster') else 0

        stats = composite.updateMask(mask).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=area, scale=10, maxPixels=1e8
        ).getInfo()

        # ESA correspondencia
        total_px = mask.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
        ).getInfo()['cluster']

        esa_str = ''
        if total_px:
            esa_parts = []
            for code, name in esa_classes.items():
                esa_mask = mask.And(esa.eq(code))
                px = esa_mask.reduceRegion(
                    reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
                ).getInfo()['cluster']
                if px and px > 0:
                    pct = px / total_px * 100
                    if pct >= 3:
                        esa_parts.append(f'{name}:{pct:.0f}%')
            esa_str = ' | '.join(esa_parts)

        idx_str = ', '.join(f'{f}={stats[f]:.3f}' for f in features if stats.get(f) is not None)
        print(f'\n  Cluster {c} ({ha:.1f} ha): {idx_str}')
        print(f'    ESA: {esa_str}')

print('\nDone.')
