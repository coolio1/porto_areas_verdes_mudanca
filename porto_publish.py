import ee
import folium
import requests
import os
import base64

ee.Initialize(project='REDACTED')

porto = ee.Geometry.Polygon([
    [[-8.70, 41.13], [-8.54, 41.13], [-8.54, 41.19], [-8.70, 41.19]]
])
BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

municipios = ee.FeatureCollection('projects/REDACTED/assets/CAOP2025_municipios')
municipiosPorto = municipios.filterBounds(porto)

BANDS = ['B3', 'B4', 'B8', 'B11', 'SCL']

def getS2col(start, end):
    """Retorna colecao processada (sem reduzir)."""
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
    """Composito multi-sazonal: mediana verao + NDVI primavera + NDVI min."""
    all_col = ee.ImageCollection([])
    spring_col = ee.ImageCollection([])

    for year in years:
        full = getS2col(f'{year}-05-01', f'{year}-10-31')
        all_col = all_col.merge(full)
        spring = getS2col(f'{year}-05-15', f'{year}-06-30')
        spring_col = spring_col.merge(spring)

    median = all_col.median().clip(porto)
    spring_ndvi = spring_col.select('ndvi').reduce(
        ee.Reducer.percentile([15])).rename('spring_ndvi').clip(porto)
    ndvi_min = all_col.select('ndvi').reduce(
        ee.Reducer.percentile([10])).rename('ndvi_min').clip(porto)

    return median.addBands(spring_ndvi).addBands(ndvi_min)

print('A calcular compositos Sentinel-2 (multi-sazonal)...')
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
ndviDrop = ndvi_e.subtract(ndvi_l)

# ESA WorldCover 10m (2021) como desempate na zona ambigua
esa = ee.Image('ESA/WorldCover/v200/2021').select('Map').clip(porto)
esaBuilt = esa.eq(50)

# Classificacao: temporal + espectral
# arvore = NDVI verao >= 0.5
#          AND NDVI primavera (Mai-Jun, p15) >= 0.7  [relva seca, arvores com folha]
#          AND NDVI min (p10) >= 0.3                  [tolerante para caducifolias]
#          AND NIR/Green >= 4                          [filtra relva regada]
#          AND B3 < 600                                [filtra vegetacao brilhante]
def classify(ndvi, ndbi, nirgreen, green, spring_ndvi, ndvi_min):
    # Arvores puras (rigoroso)
    isTreeStrict = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.7))
        .And(ndvi_min.gte(0.3))
        .And(nirgreen.gte(4))
        .And(green.lt(600))
    )
    # Verde urbano / arvores mistas (ruas arborizadas, jardins)
    isMixed = (ndvi.gte(0.5)
        .And(spring_ndvi.gte(0.5))
        .And(ndvi_min.gte(0.2))
        .And(green.lt(600))
        .And(isTreeStrict.Not())
    )
    # Arvores = puras + mistas (juntas para o mapa)
    isTree = isTreeStrict.Or(isMixed)
    # Edificado
    clear_built = ndvi.lt(0.2).And(ndbi.gte(-0.1))
    esa_tiebreak = ndvi.gte(0.2).And(ndvi.lt(0.35)).And(esaBuilt)
    isBuilt = clear_built.Or(esa_tiebreak)
    # Solo/Relva = resto
    isSolo = isTree.Not().And(isBuilt.Not())
    return isTree, isTreeStrict, isMixed, isBuilt, isSolo

isTree_e, _, _, isBuilt_e, isSolo_e = classify(ndvi_e, ndbi_e, nirgreen_e, green_e, spring_ndvi_e, ndvi_min_e)
isTree_l_base, _, _, isBuilt_l_base, _ = classify(ndvi_l, ndbi_l, nirgreen_l, green_l, spring_ndvi_l, ndvi_min_l)

# Criterio restrito: pixel edificado em 2016 so sai se NDVI 2025 >= 0.45
stays_built = isBuilt_e.And(ndvi_l.lt(0.45))
isBuilt_l = isBuilt_l_base.Or(stays_built)
isTree_l = isTree_l_base.And(isBuilt_l.Not())
isSolo_l = isTree_l.Not().And(isBuilt_l.Not())

treesToSolo  = isTree_e.And(isSolo_l).And(ndviDrop.gte(0.15))
treesToBuilt = isTree_e.And(isBuilt_l).And(ndviDrop.gte(0.15))
soloToBuilt  = isSolo_e.And(isBuilt_l).And(ndviDrop.gte(0.1))
soloToTrees  = isTree_e.Not().And(isTree_l).And(ndvi_l.subtract(ndvi_e).gte(0.15))

os.makedirs('layers', exist_ok=True)
DIM = 2048

def download_layer(image, color_hex, filename):
    """Download layer as colored PNG with transparency."""
    from PIL import Image
    import io, time

    filepath = f'layers/{filename}'
    if os.path.exists(filepath):
        print(f'  {filename} ja existe, a saltar...')
        return filepath

    vis = image.visualize(palette=[color_hex], min=0, max=1)
    for attempt in range(3):
        url = vis.getThumbURL({'region': porto, 'dimensions': DIM, 'format': 'png'})
        print(f'  A descarregar {filename}...')
        r = requests.get(url)
        try:
            img = Image.open(io.BytesIO(r.content)).convert('RGBA')
            break
        except Exception as e:
            print(f'  Tentativa {attempt+1} falhou: {e}')
            if attempt < 2:
                time.sleep(3)
            else:
                return None

    # Make black/near-black pixels transparent
    pixels = list(img.getdata())
    new_data = [(0,0,0,0) if (p[0]<10 and p[1]<10 and p[2]<10) else p for p in pixels]
    img.putdata(new_data)
    img.save(filepath)
    print(f'  {filename} guardado ({os.path.getsize(filepath)//1024} KB)')
    return filepath

def to_base64(filepath):
    with open(filepath, 'rb') as f:
        return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

# Layers: (id, ee_image, label, default_color, show_by_default)
LANDUSE_LAYERS = [
    ('uso_arvores',   isTree_l.selfMask(),  u'\u00c1rvores (2024-25)',   '228B22', False),
    ('uso_solo',      isSolo_l.selfMask(),  u'Solo (2024-25)',           'C2B280', False),
    ('uso_edificado', isBuilt_l.selfMask(), u'Edificado (2024-25)',      '888888', False),
]

TRANS_LAYERS = [
    ('arvores_edificado', treesToBuilt.selfMask(), u'\u00c1rvores \u2192 Edificado',  'D7263D', True),
    ('arvores_solo',      treesToSolo.selfMask(),  u'\u00c1rvores \u2192 Solo',       'E8A838', True),
    ('solo_edificado',    soloToBuilt.selfMask(),  u'Solo \u2192 Edificado',          '6A1B9A', True),
    ('solo_arvores',      soloToTrees.selfMask(),  u'Solo \u2192 \u00c1rvores',       '2E7D32', True),
]

ALL_LAYERS = LANDUSE_LAYERS + TRANS_LAYERS

print('\nA descarregar camadas...')
for lid, mask, label, color, show in ALL_LAYERS:
    download_layer(mask, color, f'{lid}.png')

muni_styled = ee.Image().paint(municipiosPorto, 0, 2).selfMask()
download_layer(muni_styled, 'FFFFFF', 'municipios.png')

# ============================================================
# Build HTML
# ============================================================
print('\nA construir mapa...')

m = folium.Map(location=[41.155, -8.63], zoom_start=13,
               tiles='CartoDB dark_matter', attr='CartoDB')

folium.TileLayer(
    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attr='Esri', name=u'Sat\u00e9lite', overlay=False, control=True,
).add_to(m)
folium.TileLayer('OpenStreetMap', name='OpenStreetMap', overlay=False, control=True).add_to(m)

# Add all overlay layers with base64 images
for lid, mask, label, color, show in ALL_LAYERS:
    b64 = to_base64(f'layers/{lid}.png')
    folium.raster_layers.ImageOverlay(
        image=b64, bounds=BOUNDS, name=label,
        opacity=1.0, interactive=False, show=show,
    ).add_to(m)

muni_b64 = to_base64('layers/municipios.png')
folium.raster_layers.ImageOverlay(
    image=muni_b64, bounds=BOUNDS, name='Limites municipais',
    opacity=1.0, interactive=False, show=True,
).add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# Legend with color pickers
picker_html_landuse = ''
picker_html_trans = ''
for i, (lid, mask, label, color, show) in enumerate(ALL_LAYERS):
    row = (f'<input type="color" id="c{i}" value="#{color}" data-layer="{lid}" '
           f'style="width:24px;height:24px;border:none;cursor:pointer;vertical-align:middle;margin-right:6px;">'
           f' {label}<br>')
    if i < len(LANDUSE_LAYERS):
        picker_html_landuse += row
    else:
        picker_html_trans += row

# Generate a short unique prefix from each layer's base64 to identify it in JS
# Use first 40 chars of the base64 data (after the header) as fingerprint
layer_fingerprints = {}
for i, (lid, mask, label, color, show) in enumerate(ALL_LAYERS):
    b64 = to_base64(f'layers/{lid}.png')
    # Extract a unique substring from the base64 data
    fp = b64[30:70]  # skip 'data:image/png;base64,' prefix area
    layer_fingerprints[i] = fp

fps_js = str(layer_fingerprints).replace("'", '"')

n = len(ALL_LAYERS)

legend_and_js = f"""
<div id="color-panel" style="position:fixed; bottom:30px; left:30px; z-index:1000;
     background:rgba(30,30,30,0.95); padding:16px 20px; border-radius:10px;
     font-family:'Segoe UI',Arial,sans-serif; font-size:13px; color:#eee;
     box-shadow:0 2px 10px rgba(0,0,0,0.5); line-height:2.2; min-width:280px;
     max-height:90vh; overflow-y:auto;">
<b style="font-size:14px;">Espa\u00e7o verde do Porto</b><br>
<span style="color:#aaa;font-size:10px;">2016-17 \u2192 2024-25 \u2022 Sentinel-2</span><br>
<span style="color:#aaa;font-size:10px;">Clique nos quadrados para mudar as cores:</span><br><br>

<b style="font-size:11px;color:#ccc;">Uso do solo (2024-25)</b><br>
{picker_html_landuse}
<br>
<b style="font-size:11px;color:#ccc;">Transi\u00e7\u00f5es (2016-17 \u2192 2024-25)</b><br>
{picker_html_trans}

<hr style="border-color:#555;margin:8px 0;">
<span style="color:#aaa;font-size:10px;">Fonte: Sentinel-2 (ESA)</span>
</div>

<script>
(function() {{
    var N = {n};
    var fingerprints = {fps_js};
    var masks = {{}};       // idx -> {{w, h, alpha}}
    var origSrcs = {{}};    // idx -> original base64 src
    var colored = {{}};     // idx -> current recolored dataURL

    function hexToRgb(hex) {{
        hex = hex.replace('#','');
        return [parseInt(hex.substr(0,2),16), parseInt(hex.substr(2,2),16), parseInt(hex.substr(4,2),16)];
    }}

    // Find which layer index an img belongs to, by checking its src
    function identifyImg(img) {{
        var src = img.src || '';
        // Check against fingerprints (original base64)
        for (var idx in fingerprints) {{
            if (src.indexOf(fingerprints[idx]) !== -1) return parseInt(idx);
        }}
        // Check against stored colored versions
        for (var idx in colored) {{
            if (src === colored[idx]) return parseInt(idx);
        }}
        return -1;
    }}

    function getAllOverlayImgs() {{
        return Array.from(document.querySelectorAll('.leaflet-overlay-pane .leaflet-image-layer'));
    }}

    function extractMask(src, idx) {{
        return new Promise(function(resolve) {{
            var img = new Image();
            img.onload = function() {{
                var c = document.createElement('canvas');
                c.width = img.width; c.height = img.height;
                var ctx = c.getContext('2d');
                ctx.drawImage(img, 0, 0);
                var d = ctx.getImageData(0, 0, c.width, c.height);
                var mask = new Uint8Array(d.data.length / 4);
                for (var i = 0; i < mask.length; i++) {{
                    mask[i] = d.data[i*4+3];
                }}
                masks[idx] = {{w: c.width, h: c.height, alpha: mask}};
                resolve();
            }};
            img.src = src;
        }});
    }}

    function recolor(imgEl, idx, hex) {{
        var m = masks[idx];
        if (!m) return;
        var rgb = hexToRgb(hex);
        var c = document.createElement('canvas');
        c.width = m.w; c.height = m.h;
        var ctx = c.getContext('2d');
        var d = ctx.createImageData(m.w, m.h);
        for (var i = 0; i < m.alpha.length; i++) {{
            d.data[i*4]   = rgb[0];
            d.data[i*4+1] = rgb[1];
            d.data[i*4+2] = rgb[2];
            d.data[i*4+3] = m.alpha[i];
        }}
        ctx.putImageData(d, 0, 0);
        var dataUrl = c.toDataURL();
        colored[idx] = dataUrl;
        imgEl.src = dataUrl;
    }}

    // Scan all visible overlays and apply current picker colors
    function applyAll() {{
        var imgs = getAllOverlayImgs();
        imgs.forEach(function(img) {{
            var idx = identifyImg(img);
            if (idx < 0 || idx >= N) return;
            var picker = document.getElementById('c' + idx);
            if (picker && masks[idx]) {{
                recolor(img, idx, picker.value);
            }}
        }});
    }}

    async function init() {{
        // Wait for at least some overlays
        var imgs = getAllOverlayImgs();
        if (imgs.length === 0) {{
            setTimeout(init, 500);
            return;
        }}

        // Extract masks from all visible overlays
        for (var i = 0; i < imgs.length; i++) {{
            var idx = identifyImg(imgs[i]);
            if (idx >= 0 && idx < N && !masks[idx]) {{
                origSrcs[idx] = imgs[i].src;
                await extractMask(imgs[i].src, idx);
            }}
        }}

        // Bind color pickers
        for (var i = 0; i < N; i++) {{
            (function(idx) {{
                var picker = document.getElementById('c' + idx);
                if (!picker) return;
                picker.addEventListener('input', function() {{
                    var imgs = getAllOverlayImgs();
                    imgs.forEach(function(img) {{
                        var id = identifyImg(img);
                        if (id === idx) recolor(img, idx, picker.value);
                    }});
                }});
            }})(i);
        }}

        // Don't recolor initially -- keep the original exported colors
    }}

    // When layers are toggled, Leaflet re-adds img elements with original src.
    // We need to detect new imgs and recolor them if the user changed the color.
    setInterval(function() {{
        var imgs = getAllOverlayImgs();
        imgs.forEach(function(img) {{
            var idx = identifyImg(img);
            if (idx < 0 || idx >= N) return;

            // If this img has the original src (not yet recolored) and user changed color
            var picker = document.getElementById('c' + idx);
            if (!picker) return;

            // Extract mask if we don't have it yet
            if (!masks[idx] && img.src.indexOf('data:image/png;base64,') === 0) {{
                origSrcs[idx] = img.src;
                extractMask(img.src, idx).then(function() {{
                    if (picker.value !== picker.defaultValue) {{
                        recolor(img, idx, picker.value);
                    }}
                }});
                return;
            }}

            // If user changed color and this img shows original, recolor it
            if (masks[idx] && picker.value !== picker.defaultValue) {{
                if (img.src !== colored[idx]) {{
                    recolor(img, idx, picker.value);
                }}
            }}
        }});
    }}, 500);

    setTimeout(init, 1500);
}})();
</script>
"""

m.get_root().html.add_child(folium.Element(legend_and_js))

output = 'index.html'
m.save(output)
print(f'\nMapa guardado em {output} ({os.path.getsize(output)//1024} KB)')

import webbrowser
webbrowser.open('http://localhost:8765/' + output)
