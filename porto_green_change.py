import ee

ee.Initialize(project='REDACTED')

# ============================================================
# PORTO GREEN SPACE CHANGE DETECTION 2016 → 2025
# ============================================================

# 1. AOI
porto = ee.Geometry.Polygon([
    [[-8.69, 41.13], [-8.57, 41.13], [-8.57, 41.18], [-8.69, 41.18]]
])

# 2. Confidence threshold
CONFIDENCE = 0.70

# 3. Municipality boundaries
municipios = ee.FeatureCollection('projects/REDACTED/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

# ============================================================
# 4. DYNAMIC WORLD COMPOSITE BUILDER
# ============================================================
PROB_BANDS = ['water', 'trees', 'grass', 'flooded_vegetation',
              'crops', 'shrub_and_scrub', 'built', 'bare', 'snow_and_ice']

def getDWComposite(start, end):
    dw = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
        .filterBounds(porto)
        .filterDate(start, end))

    meanProbs = dw.select(PROB_BANDS).mean()
    classification = (meanProbs.toArray()
        .arrayArgmax().arrayFlatten([['label']]))
    confidence = (meanProbs.toArray()
        .arrayReduce(ee.Reducer.max(), [0]).arrayFlatten([['confidence']]))

    return (classification.addBands(confidence)
        .addBands(meanProbs)
        .clip(porto))

dw16 = getDWComposite('2016-06-01', '2016-09-30')
dw25 = getDWComposite('2025-06-01', '2025-09-30')

# ============================================================
# 5. CONFIDENCE MASKING
# ============================================================
conf16 = dw16.select('confidence').gte(CONFIDENCE)
conf25 = dw25.select('confidence').gte(CONFIDENCE)
highConf = conf16.And(conf25)

label16 = dw16.select('label')
label25 = dw25.select('label')

# ============================================================
# 6. SIMPLE CLASSIFICATION: Green vs Not Green
# ============================================================
isGreen16 = (label16.eq(1).Or(label16.eq(2)).Or(label16.eq(3))
             .Or(label16.eq(4)).Or(label16.eq(5)))
isGreen25 = (label25.eq(1).Or(label25.eq(2)).Or(label25.eq(3))
             .Or(label25.eq(4)).Or(label25.eq(5)))

# ============================================================
# 7. CHANGE LAYERS
# ============================================================
greenLost   = isGreen16.And(isGreen25.Not()).And(highConf)
greenGained = isGreen16.Not().And(isGreen25).And(highConf)
greenStable = isGreen16.And(isGreen25).And(highConf)

# ============================================================
# 8. ESA WORLDCOVER CROSS-CHECK
# ============================================================
esa21 = ee.Image('ESA/WorldCover/v200/2021').clip(porto)
esaGreen = esa21.select('Map').lte(40)
greenLost_esaConfirmed = greenLost.And(esaGreen)

# ============================================================
# 9. DETAILED RECLASSIFICATION — for exports
# ============================================================
def reclassify(labelImg):
    return (ee.Image(0)
        .where(labelImg.eq(1), 1)
        .where(labelImg.eq(2).Or(labelImg.eq(3)).Or(labelImg.eq(4)).Or(labelImg.eq(5)), 2)
        .where(labelImg.eq(6), 3)
        .where(labelImg.eq(7), 4)
        .rename('class'))

class16 = reclassify(label16)
class25 = reclassify(label25)

treeToBuilt   = class16.eq(1).And(class25.eq(3)).And(highConf)
treeToGreen   = class16.eq(1).And(class25.eq(2)).And(highConf)
treeToBare    = class16.eq(1).And(class25.eq(4)).And(highConf)
greenToBuilt  = class16.eq(2).And(class25.eq(3)).And(highConf)
greenToBare   = class16.eq(2).And(class25.eq(4)).And(highConf)
builtToTree   = class16.eq(3).And(class25.eq(1)).And(highConf)
builtToGreen  = class16.eq(3).And(class25.eq(2)).And(highConf)
bareToTree    = class16.eq(4).And(class25.eq(1)).And(highConf)
bareToGreen   = class16.eq(4).And(class25.eq(2)).And(highConf)

pixelArea = ee.Image.pixelArea().divide(10000)  # hectares

# ============================================================
# 10. DIAGNOSTICS — quick check that data exists
# ============================================================
print('\n=== DIAGNOSTICS ===')

# Check scene counts
dw16_count = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
    .filterBounds(porto).filterDate('2016-06-01', '2016-09-30').size().getInfo())
dw25_count = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
    .filterBounds(porto).filterDate('2025-06-01', '2025-09-30').size().getInfo())
print(f'DW scenes 2016: {dw16_count}')
print(f'DW scenes 2025: {dw25_count}')

# Check green pixel counts (lightweight, single number)
green16_count = (isGreen16.reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=100, maxPixels=1e8
).get('label').getInfo())
print(f'Green pixels 2016 (at 100m): {green16_count}')

green25_count = (isGreen25.reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=100, maxPixels=1e8
).get('label').getInfo())
print(f'Green pixels 2025 (at 100m): {green25_count}')

conf_count = (highConf.reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=100, maxPixels=1e8
).get('confidence').getInfo())
print(f'High confidence pixels (at 100m): {conf_count}')

lost_count = (greenLost.reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=100, maxPixels=1e8
).get('label').getInfo())
print(f'Green lost pixels (at 100m): {lost_count}')

gained_count = (greenGained.reduceRegion(
    reducer=ee.Reducer.sum(), geometry=porto, scale=100, maxPixels=1e8
).get('label').getInfo())
print(f'Green gained pixels (at 100m): {gained_count}')

print('\n=== DIAGNOSTICS OK — submitting exports ===\n')

# ============================================================
# 11. MUNICIPALITY BREAKDOWN — export
# ============================================================
transition_list = [
    (treeToBuilt,  'tree_to_built'),
    (treeToGreen,  'tree_to_grass'),
    (treeToBare,   'tree_to_bare'),
    (greenToBuilt, 'green_to_built'),
    (greenToBare,  'green_to_bare'),
    (builtToTree,  'built_to_tree'),
    (builtToGreen, 'built_to_green'),
    (bareToTree,   'bare_to_tree'),
    (bareToGreen,  'bare_to_green'),
    (greenLost,    'total_green_loss'),
    (greenGained,  'total_green_gain'),
]

combinedStats = []
for mask, name in transition_list:
    stats = mask.multiply(pixelArea).reduceRegions(
        collection=municipiosPorto,
        reducer=ee.Reducer.sum().setOutputs([name]),
        scale=10
    )
    combinedStats.append(stats)

# Merge all columns
masterStats = combinedStats[0]
for i in range(1, len(combinedStats)):
    joinFilter = ee.Filter.equals(leftField='system:index', rightField='system:index')
    join = ee.Join.inner('primary', 'secondary')
    masterStats = (join.apply(masterStats, combinedStats[i], joinFilter)
        .map(lambda pair: (ee.Feature(None)
            .copyProperties(ee.Feature(pair.get('primary')))
            .copyProperties(ee.Feature(pair.get('secondary'))))))

masterStats = masterStats.map(lambda f: f.set(
    'net_green_change',
    ee.Number(f.get('total_green_gain')).subtract(ee.Number(f.get('total_green_loss')))
))

# ============================================================
# 12. ANNUAL TIME SERIES
# ============================================================
def annualStats(y):
    y = ee.Number(y)
    start = ee.Date.fromYMD(y, 6, 1)
    end = ee.Date.fromYMD(y, 9, 30)

    dw = (ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1')
        .filterBounds(porto).filterDate(start, end))

    meanProbs = dw.select(PROB_BANDS).mean()
    classification = meanProbs.toArray().arrayArgmax().arrayFlatten([['label']])
    confidence = meanProbs.toArray().arrayReduce(ee.Reducer.max(), [0]).arrayFlatten([['confidence']])

    classImg = reclassify(classification)
    confMask = confidence.gte(CONFIDENCE)

    treeArea = (classImg.eq(1).And(confMask).multiply(pixelArea)
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=porto, scale=10, maxPixels=1e9)
        .get('class'))

    greenArea = (classImg.eq(1).Or(classImg.eq(2)).And(confMask).multiply(pixelArea)
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=porto, scale=10, maxPixels=1e9)
        .get('class'))

    builtArea = (classImg.eq(3).And(confMask).multiply(pixelArea)
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=porto, scale=10, maxPixels=1e9)
        .get('class'))

    return ee.Feature(None, {
        'year': y, 'tree_ha': treeArea, 'green_ha': greenArea, 'built_ha': builtArea
    })

annualSeries = ee.FeatureCollection(ee.List.sequence(2016, 2025).map(annualStats))

# ============================================================
# 13. CITY-WIDE SUMMARY
# ============================================================
cityStatsFeatures = []
for mask, name in transition_list:
    ha = (mask.multiply(pixelArea).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=porto, scale=10, maxPixels=1e9
    ).get('class'))
    cityStatsFeatures.append(ee.Feature(None, {'transition': name, 'ha': ha}))

cityStats = ee.FeatureCollection(cityStatsFeatures)

# ============================================================
# 14. CHANGE RASTER
# ============================================================
changeRaster = (ee.Image(0)
    .where(treeToBuilt,  11)
    .where(treeToGreen,  12)
    .where(treeToBare,   14)
    .where(greenToBuilt, 23)
    .where(greenToBare,  24)
    .where(builtToTree,  31)
    .where(builtToGreen, 32)
    .where(bareToTree,   41)
    .where(bareToGreen,  42)
    .rename('change_code')
    .toUint8()
    .clip(porto))

# ============================================================
# 15. SUBMIT ALL EXPORTS
# ============================================================
tasks = []

t1 = ee.batch.Export.image.toDrive(
    image=changeRaster,
    description='Porto_Change_2016_2025',
    folder='porto_analysis',
    fileNamePrefix='porto_change_2016_2025',
    region=porto, scale=10, crs='EPSG:32629', maxPixels=1e9)
t1.start()
tasks.append(('Porto_Change_2016_2025', t1))

t2 = ee.batch.Export.image.toDrive(
    image=class16.toUint8().clip(porto),
    description='Porto_Class_2016',
    folder='porto_analysis',
    fileNamePrefix='porto_class_2016',
    region=porto, scale=10, crs='EPSG:32629', maxPixels=1e9)
t2.start()
tasks.append(('Porto_Class_2016', t2))

t3 = ee.batch.Export.image.toDrive(
    image=class25.toUint8().clip(porto),
    description='Porto_Class_2025',
    folder='porto_analysis',
    fileNamePrefix='porto_class_2025',
    region=porto, scale=10, crs='EPSG:32629', maxPixels=1e9)
t3.start()
tasks.append(('Porto_Class_2025', t3))

t4 = ee.batch.Export.table.toDrive(
    collection=masterStats,
    description='Porto_Municipality_Stats',
    folder='porto_analysis',
    fileNamePrefix='porto_municipality_change_stats',
    fileFormat='CSV')
t4.start()
tasks.append(('Porto_Municipality_Stats', t4))

t5 = ee.batch.Export.table.toDrive(
    collection=annualSeries,
    description='Porto_Annual_Series',
    folder='porto_analysis',
    fileNamePrefix='porto_annual_timeseries',
    fileFormat='CSV')
t5.start()
tasks.append(('Porto_Annual_Series', t5))

t6 = ee.batch.Export.table.toDrive(
    collection=cityStats,
    description='Porto_City_Summary',
    folder='porto_analysis',
    fileNamePrefix='porto_city_summary',
    fileFormat='CSV')
t6.start()
tasks.append(('Porto_City_Summary', t6))

t7 = ee.batch.Export.image.toDrive(
    image=dw25.select('confidence').toFloat().clip(porto),
    description='Porto_Confidence_2025',
    folder='porto_analysis',
    fileNamePrefix='porto_confidence_2025',
    region=porto, scale=10, crs='EPSG:32629', maxPixels=1e9)
t7.start()
tasks.append(('Porto_Confidence_2025', t7))

print('All 7 tasks submitted!\n')
for name, t in tasks:
    print(f'  {name}: {t.status()["state"]}')

print('\nFiles will appear in Google Drive -> porto_analysis/')
print('Monitor at: https://code.earthengine.google.com/tasks')

# ============================================================
# CHANGE CODE LEGEND (for exported raster):
#  0  = No confident change / stable
#  11 = Tree → Built       | 31 = Built → Tree
#  12 = Tree → Green(low)  | 32 = Built → Green(low)
#  14 = Tree → Bare        | 41 = Bare → Tree
#  23 = Green(low) → Built | 42 = Bare → Green(low)
#  24 = Green(low) → Bare  |
# ============================================================
