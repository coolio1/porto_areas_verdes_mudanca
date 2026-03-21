"""Check spectral values of specific pixels."""
import ee
import os

GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

area = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])

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

years = [2024, 2025]
all_col = ee.ImageCollection([])
spring_col = ee.ImageCollection([])
for year in years:
    all_col = all_col.merge(getS2col(f'{year}-05-01', f'{year}-10-31'))
    spring_col = spring_col.merge(getS2col(f'{year}-05-15', f'{year}-06-30'))

median = all_col.median().clip(area)
spring_ndvi = spring_col.select('ndvi').reduce(ee.Reducer.percentile([15])).rename('spring_ndvi').clip(area)
ndvi_min = all_col.select('ndvi').reduce(ee.Reducer.percentile([10])).rename('ndvi_min').clip(area)
composite = median.addBands(spring_ndvi).addBands(ndvi_min)

pixels = {
    'Arvore-como-solo 1 (41.148N)': ee.Geometry.Point([-8.670736, 41.148208]),
    'Arvore-como-solo 2 (41.173N)': ee.Geometry.Point([-8.686003, 41.173581]),
}

bands = ['ndvi', 'ndbi', 'ndmi', 'nir_green', 'b3', 'spring_ndvi', 'ndvi_min']

for name, geom in pixels.items():
    vals = composite.select(bands).reduceRegion(
        reducer=ee.Reducer.first(), geometry=geom, scale=10
    ).getInfo()
    print(f'\n=== {name} ===')
    for k in bands:
        v = vals.get(k)
        print(f'  {k}: {v:.4f}' if v is not None else f'  {k}: None')

    # Check filters
    ndvi_v = vals.get('ndvi', 0)
    spring_v = vals.get('spring_ndvi', 0)
    min_v = vals.get('ndvi_min', 0)
    nirg_v = vals.get('nir_green', 0)
    b3_v = vals.get('b3', 0)

    print(f'\n  Arvore?  NDVI>=0.5:{ndvi_v>=0.5} spring>=0.7:{spring_v>=0.7} min>=0.3:{min_v>=0.3} NIR/G>=4:{nirg_v>=4} B3<600:{b3_v<600}')
    print(f'  Misto?   NDVI>=0.5:{ndvi_v>=0.5} spring>=0.5:{spring_v>=0.5} min>=0.2:{min_v>=0.2} B3<700:{b3_v<700}')

print('\nDone.')
