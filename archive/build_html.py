"""Build index.html with pure Leaflet + embedded base64 layers."""
import base64, os

LAYERS = [
    ('uso_arvores',       u'\u00c1rvores (2024-25)',             '#228B22', False),
    ('uso_solo',          u'Solo (2024-25)',                     '#C2B280', False),
    ('uso_edificado',     u'Edificado (2024-25)',                '#888888', False),
    ('arvores_edificado', u'\u00c1rvores \u2192 Edificado',      '#D7263D', True),
    ('arvores_solo',      u'\u00c1rvores \u2192 Solo',           '#E8A838', True),
    ('solo_edificado',    u'Solo \u2192 Edificado',              '#6A1B9A', True),
    ('solo_arvores',      u'Solo \u2192 \u00c1rvores',           '#2E7D32', True),
]

BOUNDS = [[41.13, -8.70], [41.19, -8.54]]

def to_b64(filepath):
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()

# Build JS layer data
layer_js_entries = []
for lid, label, color, show in LAYERS:
    b64 = to_b64(f'layers/{lid}.png')
    layer_js_entries.append(
        f'  {{id:"{lid}", label:"{label}", color:"{color}", show:{str(show).lower()}, '
        f'src:"data:image/png;base64,{b64}"}}'
    )
layers_js = ',\n'.join(layer_js_entries)

muni_b64 = to_b64('layers/municipios.png')

html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Espaco verde do Porto - 2016-2025</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; padding:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:16px 20px; border-radius:10px;
    font-family:'Segoe UI',Arial,sans-serif; font-size:13px; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); line-height:2.0; min-width:290px;
    max-height:85vh; overflow-y:auto;
  }}
  #panel b.title {{ font-size:14px; }}
  #panel .section {{ font-size:11px; color:#ccc; margin-top:8px; }}
  #panel hr {{ border-color:#555; margin:8px 0; }}
  .layer-row {{
    display:flex; align-items:center; gap:6px; margin:2px 0;
  }}
  .layer-row input[type=color] {{
    width:24px; height:24px; border:none; cursor:pointer; padding:0;
    border-radius:3px;
  }}
  .layer-row input[type=checkbox] {{
    width:16px; height:16px; cursor:pointer;
  }}
  .layer-row label {{ cursor:pointer; }}
</style>
</head>
<body>
<div id="map"></div>
<div id="panel">
  <b class="title">Espa\u00e7o verde do Porto</b><br>
  <span style="color:#aaa;font-size:10px;">2016-17 \u2192 2024-25 \u2022 Sentinel-2</span><br>
  <span style="color:#aaa;font-size:10px;">Clique nas cores para personalizar:</span>
  <div class="section">Uso do solo (2024-25)</div>
  <div id="landuse-rows"></div>
  <div class="section">Transi\u00e7\u00f5es (2016-17 \u2192 2024-25)</div>
  <div id="trans-rows"></div>
  <hr>
  <span style="color:#aaa;font-size:10px;">Fonte: Sentinel-2 (ESA)</span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);

L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: 'CartoDB', maxZoom: 19
}}).addTo(map);

var baseMaps = {{
  "CartoDB Dark": L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{maxZoom:19}}),
  "Sat\\u00e9lite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{maxZoom:19, attribution:'Esri'}}),
  "OpenStreetMap": L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom:19, attribution:'OSM'}})
}};
L.control.layers(baseMaps, {{}}, {{collapsed: true, position:'topright'}}).addTo(map);

var bounds = {BOUNDS};
var layers = [
{layers_js}
];

// Municipios
var muniOverlay = L.imageOverlay('data:image/png;base64,{muni_b64}', bounds);
muniOverlay.addTo(map);

// For each layer: store mask, create overlay, create UI row
var state = []; // {{overlay, mask, currentColor, origSrc}}

function hexToRgb(hex) {{
  hex = hex.replace('#','');
  return [parseInt(hex.substr(0,2),16), parseInt(hex.substr(2,2),16), parseInt(hex.substr(4,2),16)];
}}

function extractMask(src) {{
  return new Promise(function(resolve) {{
    var img = new Image();
    img.onload = function() {{
      var c = document.createElement('canvas');
      c.width = img.width; c.height = img.height;
      var ctx = c.getContext('2d');
      ctx.drawImage(img, 0, 0);
      var d = ctx.getImageData(0, 0, c.width, c.height);
      var alpha = new Uint8Array(d.data.length / 4);
      for (var i = 0; i < alpha.length; i++) alpha[i] = d.data[i*4+3];
      resolve({{w: c.width, h: c.height, alpha: alpha}});
    }};
    img.src = src;
  }});
}}

function renderColored(mask, hex) {{
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = mask.w; c.height = mask.h;
  var ctx = c.getContext('2d');
  var d = ctx.createImageData(mask.w, mask.h);
  for (var i = 0; i < mask.alpha.length; i++) {{
    d.data[i*4]   = rgb[0];
    d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2];
    d.data[i*4+3] = mask.alpha[i];
  }}
  ctx.putImageData(d, 0, 0);
  return c.toDataURL();
}}

async function initLayers() {{
  var landuseDiv = document.getElementById('landuse-rows');
  var transDiv = document.getElementById('trans-rows');

  for (var i = 0; i < layers.length; i++) {{
    var L_data = layers[i];
    var mask = await extractMask(L_data.src);
    var coloredSrc = renderColored(mask, L_data.color);
    var overlay = L.imageOverlay(coloredSrc, bounds);
    if (L_data.show) overlay.addTo(map);

    state.push({{overlay: overlay, mask: mask, currentColor: L_data.color}});

    // Create UI row
    var row = document.createElement('div');
    row.className = 'layer-row';

    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = L_data.show;
    cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = parseInt(this.dataset.idx);
      if (this.checked) state[idx].overlay.addTo(map);
      else map.removeLayer(state[idx].overlay);
    }});

    var cp = document.createElement('input');
    cp.type = 'color';
    cp.value = L_data.color;
    cp.dataset.idx = i;
    cp.addEventListener('input', function() {{
      var idx = parseInt(this.dataset.idx);
      var s = state[idx];
      s.currentColor = this.value;
      var newSrc = renderColored(s.mask, this.value);
      s.overlay.setUrl(newSrc);
    }});

    var lbl = document.createElement('label');
    lbl.textContent = L_data.label;
    lbl.style.cursor = 'pointer';
    lbl.addEventListener('click', function() {{
      cb.click();
    }});

    row.appendChild(cb);
    row.appendChild(cp);
    row.appendChild(lbl);

    if (i < 3) landuseDiv.appendChild(row);
    else transDiv.appendChild(row);
  }}
}}

initLayers();
</script>
</body>
</html>'''

with open('mapa.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'mapa.html gerado ({os.path.getsize("mapa.html")//1024} KB)')
