"""Visualizar clusters k=6 na area de teste (3+4 juntos)."""
import ee
import requests
import os
import io
import base64

GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

LAT, LON = 41.188117, -8.617633
BUFFER = 1500

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

coords = area.coordinates().getInfo()[0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BOUNDS = [[min(lats), min(lons)], [max(lats), max(lons)]]

BANDS = ['B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11', 'SCL']

def getS2(start, end):
    s2 = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(area).filterDate(start, end)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
        .select(BANDS))
    def process(img):
        scl = img.select('SCL')
        # 4=vegetation, 5=bare soil, 6=water, 2=dark area
        # Excluir: 1=sat/defective, 3=cloud shadow, 7=unclassified, 8=cloud med, 9=cloud high, 10=cirrus, 11=snow
        clear = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6)).Or(scl.eq(2))
        ndvi = img.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndmi = img.normalizedDifference(['B8', 'B11']).rename('ndmi')
        nir_green = img.select('B8').divide(img.select('B3').max(1)).rename('nir_green')
        b3 = img.select('B3').rename('b3')
        ndre = img.normalizedDifference(['B8', 'B5']).rename('ndre')
        re_ratio = img.select('B6').divide(img.select('B5').max(1)).rename('re_ratio')
        return (ndvi.addBands(ndmi).addBands(nir_green).addBands(b3)
                .addBands(ndre).addBands(re_ratio).updateMask(clear))
    return s2.map(process).median().clip(area)

print('A calcular composito...')
s2 = getS2('2024-05-01', '2025-10-31')

features = ['ndvi', 'ndmi', 'nir_green', 'b3', 'ndre', 're_ratio']
composite = s2.select(features)

# K-means k=8
K = 8
print(f'A fazer clustering k={K}...')
training = composite.sample(region=area, scale=10, numPixels=5000, seed=42)
clusterer = ee.Clusterer.wekaKMeans(K).train(training)
clustered = composite.cluster(clusterer).rename('cluster')

# Identificar clusters por perfil espectral
print('A identificar clusters...')
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(area)
pixel_area_img = ee.Image.pixelArea()

cluster_info = []
for c in range(K):
    mask = clustered.eq(c)
    stats = composite.updateMask(mask).reduceRegion(
        reducer=ee.Reducer.mean(), geometry=area, scale=10, maxPixels=1e8
    ).getInfo()
    area_m2 = mask.multiply(pixel_area_img).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
    ).getInfo()
    ha = area_m2['cluster'] / 10000 if area_m2.get('cluster') else 0

    # ESA dominante
    total_px = mask.reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
    ).getInfo().get('cluster', 0)
    esa_tree_pct = 0
    esa_grass_pct = 0
    esa_built_pct = 0
    if total_px:
        for code, attr in [(10, 'tree'), (30, 'grass'), (50, 'built')]:
            px = mask.And(esa.eq(code)).reduceRegion(
                reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
            ).getInfo().get('cluster', 0)
            pct = px / total_px * 100 if px else 0
            if attr == 'tree': esa_tree_pct = pct
            elif attr == 'grass': esa_grass_pct = pct
            elif attr == 'built': esa_built_pct = pct

    info = {
        'id': c, 'ha': ha,
        'ndvi': stats.get('ndvi', 0), 'ndmi': stats.get('ndmi', 0),
        'ndre': stats.get('ndre', 0), 're_ratio': stats.get('re_ratio', 0),
        'nir_green': stats.get('nir_green', 0), 'b3': stats.get('b3', 0),
        'esa_tree': esa_tree_pct, 'esa_grass': esa_grass_pct, 'esa_built': esa_built_pct,
    }
    cluster_info.append(info)
    print(f'  C{c}: {ha:.0f}ha NDVI={info["ndvi"]:.3f} NDRE={info["ndre"]:.3f} '
          f'RE={info["re_ratio"]:.2f} ESA: tree={esa_tree_pct:.0f}% grass={esa_grass_pct:.0f}% built={esa_built_pct:.0f}%')

# Ordenar por NDVI decrescente
cluster_info.sort(key=lambda x: -x['ndvi'])

# Agrupar automaticamente: vegetacao (NDVI>0.35) vs edificado (NDVI<0.35)
veg_clusters = [c for c in cluster_info if c['ndvi'] >= 0.35]
built_clusters = [c for c in cluster_info if c['ndvi'] < 0.35]

print(f'\nVegetacao ({len(veg_clusters)} clusters):')
for c in veg_clusters:
    print(f'  C{c["id"]}: NDVI={c["ndvi"]:.3f} NDRE={c["ndre"]:.3f} RE={c["re_ratio"]:.2f} '
          f'tree={c["esa_tree"]:.0f}% grass={c["esa_grass"]:.0f}%')

print(f'\nEdificado ({len(built_clusters)} clusters):')
for c in built_clusters:
    print(f'  C{c["id"]}: NDVI={c["ndvi"]:.3f} built={c["esa_built"]:.0f}%')

# Criar mascaras para cada cluster de vegetacao + 1 edificado combinado
masks = []
for c in veg_clusters:
    masks.append(('veg_' + str(c['id']), clustered.eq(c['id']),
                  f'Veg C{c["id"]} (NDVI={c["ndvi"]:.2f}, tree={c["esa_tree"]:.0f}%, grass={c["esa_grass"]:.0f}%)'))

# Juntar todos os edificados
edif_mask = clustered.eq(built_clusters[0]['id'])
for c in built_clusters[1:]:
    edif_mask = edif_mask.Or(clustered.eq(c['id']))
masks.append(('edificado', edif_mask, 'Edificado (todos)'))

# --- Descarregar camadas ---
os.makedirs('layers/test', exist_ok=True)
DIM = 1024

def download_layer(image, color_hex, filename):
    from PIL import Image
    import time
    filepath = f'layers/test/{filename}'
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar {filename}...')
    for attempt in range(3):
        r = requests.get(url, timeout=120)
        try:
            img = Image.open(io.BytesIO(r.content)).convert('RGBA')
            break
        except Exception:
            print(f'    Retry {attempt+1}...')
            time.sleep(2)
    else:
        print(f'    FALHOU: {filename}')
        return
    pixels = list(img.getdata())
    new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
    img.putdata(new_data)
    img.save(filepath)

def download_rgb():
    from PIL import Image
    filepath = 'layers/test/rgb_recente.png'
    s2_rgb = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(area).filterDate('2024-05-01', '2025-10-31')
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(['B4', 'B3', 'B2']).median().clip(area))
    vis = s2_rgb.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar rgb_recente.png...')
    r = requests.get(url)
    img = Image.open(io.BytesIO(r.content)).convert('RGBA')
    img.save(filepath)

# Cores para clusters de vegetacao (do mais verde ao menos)
veg_colors = ['#1B5E20', '#2E7D32', '#388E3C', '#4CAF50', '#8BC34A', '#CDDC39', '#FFB74D', '#FF8A65']

print('\nA descarregar camadas...')
download_rgb()
for i, (mid, mask, label) in enumerate(masks):
    color = veg_colors[i] if mid != 'edificado' else '888888'
    download_layer(mask.selfMask(), color.replace('#',''), f'cl_{mid}.png')

# --- Gerar HTML ---
def to_b64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()

test_layers = []
for i, (mid, mask, label) in enumerate(masks):
    color = veg_colors[i] if mid != 'edificado' else '#888888'
    test_layers.append((f'cl_{mid}', label, color, True))

layer_js = ',\n'.join([
    f'  {{id:"{lid}", label:"{lbl}", color:"{c}", show:{str(s).lower()}, '
    f'src:"data:image/png;base64,{to_b64(f"layers/test/{lid}.png")}"}}'
    for lid, lbl, c, s in test_layers
])

rgb_b64 = to_b64('layers/test/rgb_recente.png')
center_lat = (BOUNDS[0][0] + BOUNDS[1][0]) / 2
center_lon = (BOUNDS[0][1] + BOUNDS[1][1]) / 2

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Clusters k=6 - Area teste</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }} #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{ position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',sans-serif; color:#eee; line-height:2.0; }}
  .row {{ display:flex; align-items:center; gap:6px; }}
  .row input[type=color] {{ width:22px; height:22px; border:none; cursor:pointer; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b>Clusters k={K} (Red Edge)</b><br>
  <span style="color:#aaa;font-size:10px;">NDVI+NDMI+NIR/Green+B3+NDRE+RE_ratio | 2024-26</span>
  <div id="rows"></div>
</div>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], 14);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  maxZoom:19, attribution:'Esri'
}}).addTo(map);
var bounds = {BOUNDS};
L.imageOverlay('data:image/png;base64,{rgb_b64}', bounds, {{opacity:0.5}}).addTo(map);
var layers = [{layer_js}];
var state = [];
function hexToRgb(h){{ h=h.replace('#',''); return [parseInt(h.substr(0,2),16),parseInt(h.substr(2,2),16),parseInt(h.substr(4,2),16)]; }}
function extractMask(src){{ return new Promise(function(r){{ var i=new Image(); i.onload=function(){{ var c=document.createElement('canvas'); c.width=i.width;c.height=i.height; var x=c.getContext('2d'); x.drawImage(i,0,0); var d=x.getImageData(0,0,c.width,c.height); var a=new Uint8Array(d.data.length/4); for(var j=0;j<a.length;j++) a[j]=d.data[j*4+3]; r({{w:c.width,h:c.height,alpha:a}}); }}; i.src=src; }}); }}
function renderColored(m,hex){{ var rgb=hexToRgb(hex); var c=document.createElement('canvas'); c.width=m.w;c.height=m.h; var x=c.getContext('2d'); var d=x.createImageData(m.w,m.h); for(var i=0;i<m.alpha.length;i++){{ d.data[i*4]=rgb[0];d.data[i*4+1]=rgb[1];d.data[i*4+2]=rgb[2];d.data[i*4+3]=m.alpha[i]; }} x.putImageData(d,0,0); return c.toDataURL(); }}
async function init(){{
  var div=document.getElementById('rows');
  for(var i=0;i<layers.length;i++){{
    var L_=layers[i], m=await extractMask(L_.src), cs=renderColored(m,L_.color);
    var ov=L.imageOverlay(cs,bounds); if(L_.show) ov.addTo(map);
    state.push({{overlay:ov,mask:m,color:L_.color}});
    var row=document.createElement('div'); row.className='row';
    var cb=document.createElement('input'); cb.type='checkbox'; cb.checked=L_.show; cb.dataset.idx=i;
    cb.addEventListener('change',function(){{ var idx=+this.dataset.idx; if(this.checked) state[idx].overlay.addTo(map); else map.removeLayer(state[idx].overlay); }});
    var cp=document.createElement('input'); cp.type='color'; cp.value=L_.color; cp.dataset.idx=i;
    cp.addEventListener('input',function(){{ var idx=+this.dataset.idx; var s=state[idx]; s.color=this.value; s.overlay.setUrl(renderColored(s.mask,this.value)); }});
    var lb=document.createElement('label'); lb.textContent=L_.label;
    row.appendChild(cb); row.appendChild(cp); row.appendChild(lb); div.appendChild(row);
  }}
}}
init();
</script>
</body>
</html>'''

with open('test_clusters.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\ntest_clusters.html gerado')

import webbrowser
webbrowser.open('test_clusters.html')
