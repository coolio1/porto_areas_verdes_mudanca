import ee
import folium

ee.Initialize(project='REDACTED')

porto = ee.Geometry.Polygon([
    [[-8.69, 41.13], [-8.57, 41.13], [-8.57, 41.18], [-8.69, 41.18]]
])

municipios = ee.FeatureCollection('projects/REDACTED/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

BANDS = ['B4', 'B8', 'B11', 'SCL']

def getS2(start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(porto).filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(BANDS))
    def process(img):
        scl = img.select('SCL')
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2)).Or(scl.eq(11))
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi = img.normalizedDifference(['B11', 'B8']).rename('ndbi')
        return ndvi.addBands(ndbi).updateMask(clear)
    return s2.map(process).median().clip(porto)

# 2-year windows for robust composites
s2_early = getS2('2016-05-01', '2017-10-31')
s2_late  = getS2('2024-05-01', '2025-10-31')

ndvi_e = s2_early.select('ndvi')
ndvi_l = s2_late.select('ndvi')
ndbi_l = s2_late.select('ndbi')
ndviDrop = ndvi_e.subtract(ndvi_l)

isTree_e = ndvi_e.gte(0.5)
isBare_e = ndvi_e.gte(0.2).And(ndvi_e.lt(0.5))
isTree_l = ndvi_l.gte(0.5)

treesToBuilt = isTree_e.And(ndvi_l.lt(0.3)).And(ndbi_l.gte(0)).And(ndviDrop.gte(0.15))
treesToBare  = isTree_e.And(ndvi_l.lt(0.3)).And(ndbi_l.lt(0)).And(ndviDrop.gte(0.15))
bareToBuilt  = isBare_e.And(ndvi_l.lt(0.2)).And(ndbi_l.gte(0)).And(ndviDrop.gte(0.1))
bareToTrees  = isBare_e.And(isTree_l).And(ndvi_l.subtract(ndvi_e).gte(0.15))

# ============================================================
# FOLIUM MAP
# ============================================================
def get_ee_tile_url(image, vis_params):
    return image.getMapId(vis_params)['tile_fetcher'].url_format

print('A gerar camadas...')

m = folium.Map(location=[41.155, -8.63], zoom_start=13,
               tiles='CartoDB dark_matter', attr='CartoDB')

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name='Satelite', overlay=False, control=True,
).add_to(m)
folium.TileLayer('OpenStreetMap', name='OpenStreetMap', overlay=False, control=True).add_to(m)

layers = [
    ('Arvores perdidas para edificado',    treesToBuilt.selfMask(), {'palette': ['D7263D']}),
    ('Arvores perdidas para solo exposto', treesToBare.selfMask(),  {'palette': ['E8A838']}),
    ('Solo verde perdido para edificado',  bareToBuilt.selfMask(),  {'palette': ['7B2D26']}),
    ('Solo verde convertido em arvores',   bareToTrees.selfMask(),  {'palette': ['1B7340']}),
]

for name, img, vis in layers:
    url = get_ee_tile_url(img, vis)
    folium.TileLayer(
        tiles=url, attr='Google Earth Engine',
        name=name, overlay=True, control=True, show=True,
    ).add_to(m)

# NDVI reference layers
ndvi_pal = ['8B0000','D73027','FC8D59','FEE08B','D9EF8B','66BD63','1A9850','004529']
ndvi_e_url = get_ee_tile_url(ndvi_e, {'min': 0, 'max': 0.8, 'palette': ndvi_pal})
ndvi_l_url = get_ee_tile_url(ndvi_l, {'min': 0, 'max': 0.8, 'palette': ndvi_pal})
folium.TileLayer(tiles=ndvi_e_url, attr='GEE', name='NDVI 2016-17', overlay=True, control=True, show=False).add_to(m)
folium.TileLayer(tiles=ndvi_l_url, attr='GEE', name='NDVI 2024-25', overlay=True, control=True, show=False).add_to(m)

# NDVI difference
ndviDrop_vis = ndviDrop.clamp(-0.2, 0.4).clip(porto)
ndviDiff_url = get_ee_tile_url(ndviDrop_vis, {'min': -0.2, 'max': 0.4, 'palette': ['2166AC','67A9CF','D1E5F0','F7F7F7','FDDBC7','EF8A62','B2182B']})
folium.TileLayer(tiles=ndviDiff_url, attr='GEE', name='Diferenca NDVI', overlay=True, control=True, show=False).add_to(m)

muniUrl = get_ee_tile_url(
    municipiosPorto.style(color='FFFFFF', fillColor='00000000', width=2), {})
folium.TileLayer(tiles=muniUrl, attr='GEE', name='Limites municipais',
    overlay=True, control=True, show=True).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

legend_html = u"""
<div style="position:fixed; bottom:30px; left:30px; z-index:1000;
     background:rgba(30,30,30,0.92); padding:16px 20px; border-radius:10px;
     font-family:'Segoe UI',Arial,sans-serif; font-size:12px; color:#eee;
     box-shadow:0 2px 10px rgba(0,0,0,0.5); line-height:1.8;">
<b style="font-size:14px;">Altera\u00e7\u00f5es do espa\u00e7o verde</b><br>
<span style="color:#aaa;font-size:10px;">Porto \u2022 2016-17 \u2192 2024-25 \u2022 Sentinel-2</span><br><br>
<span style="display:inline-block;width:12px;height:12px;background:#D7263D;border-radius:2px;vertical-align:middle;margin-right:6px;"></span> \u00c1rvores perdidas para edificado<br>
<span style="display:inline-block;width:12px;height:12px;background:#E8A838;border-radius:2px;vertical-align:middle;margin-right:6px;"></span> \u00c1rvores perdidas para solo exposto<br>
<span style="display:inline-block;width:12px;height:12px;background:#7B2D26;border-radius:2px;vertical-align:middle;margin-right:6px;"></span> Solo verde perdido para edificado<br>
<span style="display:inline-block;width:12px;height:12px;background:#1B7340;border-radius:2px;vertical-align:middle;margin-right:6px;"></span> Solo verde convertido em \u00e1rvores<br>
<hr style="border-color:#555;margin:8px 0;">
<span style="color:#aaa;font-size:10px;">Camadas de refer\u00eancia: NDVI e Diferen\u00e7a NDVI</span>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

output = 'porto_green_change_map.html'
m.save(output)
print(f'Mapa guardado em {output}')

import webbrowser
webbrowser.open('http://localhost:8765/' + output)

# ============================================================
# STATISTICS (scale=30 for speed, accurate enough for hectares)
# ============================================================
import sys
if '--stats' in sys.argv:
    pixelArea = ee.Image.pixelArea().divide(10000)
    SCALE = 30

    transition_list = [
        (treesToBuilt, 'Arvores perdidas para edificado'),
        (treesToBare,  'Arvores perdidas para solo exposto'),
        (bareToBuilt,  'Solo verde perdido para edificado'),
        (bareToTrees,  'Solo verde convertido em arvores'),
    ]

    print('\n=== TOTAIS PORTO ===')
    total_loss = 0
    total_gain = 0
    for mask, name in transition_list:
        ha = (mask.multiply(pixelArea)
            .reduceRegion(reducer=ee.Reducer.sum(), geometry=porto, scale=SCALE, maxPixels=1e9)
            .values().get(0).getInfo())
        print(f'  {name}: {ha:.1f} ha')
        if 'convertido em' in name:
            total_gain += ha
        else:
            total_loss += ha

    print(f'\n  Total perdas: {total_loss:.1f} ha')
    print(f'  Total ganhos: {total_gain:.1f} ha')
    print(f'  Saldo: {total_gain - total_loss:+.1f} ha')

    # --- Per municipality ---
    print('\n=== POR MUNICIPIO ===')

    # First check what property name holds the municipality name
    sample = municipiosPorto.first().propertyNames().getInfo()
    print(f'  (propriedades: {sample})')

    for mask, name in transition_list:
        stats = (mask.multiply(pixelArea)
            .reduceRegions(
                collection=municipiosPorto,
                reducer=ee.Reducer.sum(),
                scale=SCALE
            ).getInfo())
        print(f'\n  {name}:')
        for f in sorted(stats['features'], key=lambda x: x['properties'].get('sum', 0), reverse=True):
            props = f['properties']
            muni_name = (props.get('municipio') or props.get('Municipio')
                         or props.get('NOME') or props.get('NAME_2')
                         or props.get('Concelho') or 'desconhecido')
            ha = props.get('sum', 0)
            if ha > 0.1:
                print(f'    {muni_name}: {ha:.1f} ha')
