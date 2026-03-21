"""Test classification on small area around Serralves (500m buffer)."""
import ee
import requests
import os
import io
import base64

GEE_PROJECT = os.environ["GEE_PROJECT"]
ee.Initialize(project=GEE_PROJECT)

# 41°11'17.22"N 8°37'03.48"W
LAT, LON = 41.188117, -8.617633
BUFFER = 1500  # meters

point = ee.Geometry.Point([LON, LAT])
area = point.buffer(BUFFER).bounds()

# Get bounding box for image overlay
coords = area.coordinates().getInfo()[0]
lons = [c[0] for c in coords]
lats = [c[1] for c in coords]
BOUNDS = [[min(lats), min(lons)], [max(lats), max(lons)]]

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
    """Retorna colecao processada (sem reduzir)."""
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

def getComposite(years):
    """Composito multi-sazonal para separar arvores de relva.

    Estrategia: arvores caducifolias perdem folha no inverno,
    relva seca no final da primavera (Mai-Jun) e outono (Out).
    A janela Mai-Jun e a chave: arvores com folha completa, relva seca.
    """
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])

    for year in years:
        # Colecao completa (Mai-Out) para mediana geral
        full = getS2col(f'{year}-05-01', f'{year}-10-31')
        all_col = all_col.merge(full)
        # Janela primavera tardia (Mai-Jun) - arvores verdes, relva seca
        spring = getS2col(f'{year}-05-15', f'{year}-06-30')
        spring_col = spring_col.merge(spring)

    median = all_col.median().clip(area)
    # NDVI MINIMO de Mai-Jun: arvores >0.7, relva cai a <0.5
    spring_ndvi = spring_col.select('ndvi').reduce(ee.Reducer.percentile([15])).rename('spring_ndvi').clip(area)
    # NDVI minimo (p10) como backup - relva oscila, arvores estaveis
    ndvi_min = all_col.select('ndvi').reduce(ee.Reducer.percentile([10])).rename('ndvi_min').clip(area)

    return median.addBands(spring_ndvi).addBands(ndvi_min)

print('A calcular compositos...')
print(f'  Area: {BUFFER}m em redor de {LAT}N, {abs(LON)}W')

s2_early = getComposite([2016, 2017])
s2_late  = getComposite([2024, 2025])

# Contar cenas disponiveis
n_early = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(area).filterDate('2015-06-01', '2017-12-31')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).size().getInfo())
n_late = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(area).filterDate('2024-01-01', '2026-03-20')
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).size().getInfo())
print(f'  Cenas periodo antigo: {n_early}')
print(f'  Cenas periodo recente: {n_late}')

ndvi_e = s2_early.select('ndvi')
ndvi_l = s2_late.select('ndvi')
ndbi_e = s2_early.select('ndbi')
ndbi_l = s2_late.select('ndbi')
ndmi_e = s2_early.select('ndmi')
ndmi_l = s2_late.select('ndmi')
nirgreen_e = s2_early.select('nir_green')
nirgreen_l = s2_late.select('nir_green')
b3_e = s2_early.select('b3')
b3_l = s2_late.select('b3')
ndvi_min_e = s2_early.select('ndvi_min')
ndvi_min_l = s2_late.select('ndvi_min')
spring_ndvi_e = s2_early.select('spring_ndvi')
spring_ndvi_l = s2_late.select('spring_ndvi')

# ESA WorldCover 10m (2021) como desempate
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(area)
esaBuilt = esa.eq(50)

# --- Classificacao ---
# Abordagem multi-sazonal:
#   arvore = NDVI verao >= 0.5
#            AND NDVI primavera (Mai-Jun) >= 0.6  [relva seca, arvores com folha]
#            AND NDVI min (p10) >= 0.3             [arvores caducifolias podem cair, mas nao tanto]
#   edificado = (NDVI < 0.2 AND NDBI >= -0.1) OR (ESA tiebreak)
#   solo/relva = resto

def classify(ndvi, ndbi, ndmi, nirgreen, b3, ndvi_min, spring_ndvi):
    # Arvores puras: filtros temporais + espectrais
    # B3<600 OU (B3<800 se NDVI_min>=0.5) - arvores claras com NDVI estavel todo o ano
    b3_ok = b3.lt(600).Or(b3.lt(800).And(ndvi_min.gte(0.5)))
    isTree = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(b3_ok)
    )
    # Verde urbano / arvores mistas (ruas arborizadas, jardins)
    # Mesma logica B3 relaxada para NDVI_min alto
    b3_ok_mixed = b3.lt(600).Or(b3.lt(800).And(ndvi_min.gte(0.5)))
    isMixed = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(b3_ok_mixed)
        .And(isTree.Not())
    )
    # Edificado
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    # Solo/relva = resto
    isSolo = isTree.Not().And(isMixed.Not()).And(isBuilt.Not())
    return isTree, isMixed, isBuilt, isSolo

isTree_e, isMixed_e, isBuilt_e, isSolo_e = classify(ndvi_e, ndbi_e, ndmi_e, nirgreen_e, b3_e, ndvi_min_e, spring_ndvi_e)
isTree_l_base, isMixed_l_base, isBuilt_l_base, _ = classify(ndvi_l, ndbi_l, ndmi_l, nirgreen_l, b3_l, ndvi_min_l, spring_ndvi_l)

# Criterio restrito: pixel edificado em periodo antigo so sai se NDVI recente >= 0.45
stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isMixed_l = isMixed_l_base.And(isBuilt_l.Not()).And(isTree_l.Not())
isSolo_l = isTree_l.Not().And(isMixed_l.Not()).And(isBuilt_l.Not())

# Transicoes
ndviDrop = ndvi_e.subtract(ndvi_l)
treesToSolo  = isTree_e.And(isSolo_l).And(ndviDrop.gte(0.15))
treesToBuilt = isTree_e.And(isBuilt_l).And(ndviDrop.gte(0.15))
soloToBuilt  = isSolo_e.And(isBuilt_l).And(ndviDrop.gte(0.1))
soloToTrees  = isTree_e.Not().And(isTree_l).And(ndvi_l.subtract(ndvi_e).gte(0.15))

# --- Imprimir estatisticas da area ---
print('\n--- Estatisticas da area de teste ---')
pixel_area = ee.Image.pixelArea()

def count_ha(mask, label):
    area_m2 = mask.multiply(pixel_area).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=10, maxPixels=1e8
    ).getInfo()
    key = list(area_m2.keys())[0]
    ha = area_m2[key] / 10000 if area_m2[key] else 0
    print(f'  {label}: {ha:.2f} ha')
    return ha

print('\nPeriodo antigo (2015-17):')
count_ha(isTree_e.selfMask(), 'Arvores')
count_ha(isMixed_e.selfMask(), 'Verde urbano')
count_ha(isSolo_e.selfMask(), 'Solo/Relva')
count_ha(isBuilt_e.selfMask(), 'Edificado')

print('\nPeriodo recente (2024-26):')
count_ha(isTree_l.selfMask(), 'Arvores')
count_ha(isMixed_l.selfMask(), 'Verde urbano')
count_ha(isSolo_l.selfMask(), 'Solo/Relva')
count_ha(isBuilt_l.selfMask(), 'Edificado')

print('\nTransicoes:')
count_ha(treesToBuilt.selfMask(), 'Arvores -> Edificado')
count_ha(treesToSolo.selfMask(), 'Arvores -> Solo')
count_ha(soloToBuilt.selfMask(), 'Solo -> Edificado')
count_ha(soloToTrees.selfMask(), 'Solo -> Arvores')

# --- Imprimir valores medios dos indices na area (para calibrar limiares) ---
print('\n--- Valores medios dos indices ---')
def print_stats(composite, label):
    stats = composite.reduceRegion(
        reducer=ee.Reducer.percentile([10, 25, 50, 75, 90]),
        geometry=area, scale=10, maxPixels=1e8
    ).getInfo()
    print(f'\n  {label}:')
    for k, v in sorted(stats.items()):
        if v is not None:
            print(f'    {k}: {v:.4f}')

print_stats(ndvi_l, 'NDVI mediana verao (todos pixels)')
print_stats(spring_ndvi_l, 'NDVI primavera Mai-Jun (todos pixels)')
print_stats(ndvi_min_l, 'NDVI min p10 (todos pixels)')
print_stats(ndmi_l, 'NDMI recente (todos pixels)')
print_stats(nirgreen_l, 'NIR/Green recente (todos pixels)')
print_stats(b3_l, 'B3 recente (todos pixels)')

# Estatisticas SO para pixels com NDVI >= 0.5 (zona de confusao arvore vs relva)
green_mask = ndvi_l.gte(0.5)
print('\n--- Indices SO onde NDVI >= 0.5 (zona de confusao) ---')
print_stats(ndmi_l.updateMask(green_mask), 'NDMI (onde NDVI>=0.5)')
print_stats(nirgreen_l.updateMask(green_mask), 'NIR/Green (onde NDVI>=0.5)')
print_stats(b3_l.updateMask(green_mask), 'B3 (onde NDVI>=0.5)')
print_stats(spring_ndvi_l.updateMask(green_mask), 'NDVI primavera (onde NDVI>=0.5)')
print_stats(ndvi_min_l.updateMask(green_mask), 'NDVI min p10 (onde NDVI>=0.5)')
print_stats(ndvi_l.updateMask(green_mask), 'NDVI (onde NDVI>=0.5)')

# --- Validacao contra ESA WorldCover ---
print('\n--- Validacao contra ESA WorldCover (2021) ---')
esaTree = esa.eq(10)       # Tree cover
esaGrass = esa.eq(30)      # Grassland
esaShrub = esa.eq(20)      # Shrubland
esaCrop = esa.eq(40)       # Cropland
esaBuiltESA = esa.eq(50)   # Built-up

# Dos nossos "arvores", quantos sao arvores vs relva no ESA?
our_trees = isTree_l.selfMask()
trees_on_esaTree = our_trees.And(esaTree)
trees_on_esaGrass = our_trees.And(esaGrass)
trees_on_esaShrub = our_trees.And(esaShrub)
trees_on_esaCrop = our_trees.And(esaCrop)
trees_on_esaBuilt = our_trees.And(esaBuiltESA)

ha_total = count_ha(our_trees, 'Total classificado como arvore')
ha_esa_tree = count_ha(trees_on_esaTree.selfMask(), '  -> ESA: Tree cover')
ha_esa_grass = count_ha(trees_on_esaGrass.selfMask(), '  -> ESA: Grassland (RELVA!)')
ha_esa_shrub = count_ha(trees_on_esaShrub.selfMask(), '  -> ESA: Shrubland')
ha_esa_crop = count_ha(trees_on_esaCrop.selfMask(), '  -> ESA: Cropland')
ha_esa_built = count_ha(trees_on_esaBuilt.selfMask(), '  -> ESA: Built-up')

if ha_total > 0:
    pct_correct = ha_esa_tree / ha_total * 100
    pct_grass = ha_esa_grass / ha_total * 100
    print(f'\n  Precisao (vs ESA trees): {pct_correct:.1f}%')
    print(f'  Contaminacao relva: {pct_grass:.1f}%')

# Arvores ESA que nos NAO classificamos (omissao)
esa_trees_total = count_ha(esaTree.selfMask(), '\nTotal ESA Tree cover na area')
missed = esaTree.And(isTree_l.Not())
ha_missed = count_ha(missed.selfMask(), '  -> Nao classificadas por nos (omissao)')

# --- Descarregar camadas para visualizacao ---
os.makedirs('layers/test', exist_ok=True)
DIM = 1024

def download_layer(image, color_hex, filename):
    from PIL import Image
    filepath = f'layers/test/{filename}'
    vis = image.visualize(palette=[color_hex], min=0, max=1)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar {filename}...')
    r = requests.get(url)
    img = Image.open(io.BytesIO(r.content)).convert('RGBA')
    pixels = list(img.getdata())
    new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
    img.putdata(new_data)
    img.save(filepath)
    return filepath

# Tambem descarregar imagem RGB true-color para referencia
def download_rgb(composite, filename):
    from PIL import Image
    filepath = f'layers/test/{filename}'
    # Criar RGB a partir da composite S2 original
    s2_rgb = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(area).filterDate('2024-01-01', '2026-03-20')
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
        .select(['B4', 'B3', 'B2']).median().clip(area))
    vis = s2_rgb.visualize(bands=['B4', 'B3', 'B2'], min=0, max=3000)
    url = vis.getThumbURL({'region': area, 'dimensions': DIM, 'format': 'png'})
    print(f'  A descarregar {filename}...')
    r = requests.get(url)
    img = Image.open(io.BytesIO(r.content)).convert('RGBA')
    img.save(filepath)
    return filepath

print('\nA descarregar camadas de teste...')
download_rgb(s2_late, 'rgb_recente.png')
download_layer(isTree_l.selfMask(), '1B5E20', 'arvores_recente.png')
download_layer(isMixed_l.selfMask(), '66BB6A', 'misto_recente.png')
download_layer(isSolo_l.selfMask(), 'C2B280', 'solo_recente.png')
download_layer(isBuilt_l.selfMask(), '888888', 'edificado_recente.png')

# --- Gerar HTML simples para inspeccao ---
def to_b64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()

test_layers = [
    ('arvores_recente', 'Arvores', '#1B5E20', True),
    ('misto_recente', 'Verde urbano', '#66BB6A', True),
    ('solo_recente', 'Solo/Relva', '#C2B280', False),
    ('edificado_recente', 'Edificado', '#888888', False),
]

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
<title>Teste classificacao - Serralves</title>
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
  <b>Teste: 500m Serralves</b><br>
  <span style="color:#aaa;font-size:10px;">NDVI+NIR/Green+NDMI | 2024-26</span>
  <div id="rows"></div>
</div>
<script>
var map = L.map('map').setView([{center_lat}, {center_lon}], 16);
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
  maxZoom:19, attribution:'Esri'
}}).addTo(map);
var bounds = {BOUNDS};
// RGB reference
L.imageOverlay('data:image/png;base64,{rgb_b64}', bounds, {{opacity:0.7}}).addTo(map);
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

with open('test_area.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'\ntest_area.html gerado')

import webbrowser
webbrowser.open('test_area.html')
