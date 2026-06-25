"""Gera ndvi_historico.html a partir das camadas PNG já calculadas."""
import base64
import io
import os
import webbrowser
from PIL import Image


def build_html(script_dir, layers_dir, bounds, bounds_1947, epochs, layers_1947, wms_url, wms_layer):
    """Constrói mapa HTML do histórico NDVI e escreve para script_dir."""

    def to_base64(filepath):
        with open(filepath, 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()

    def to_base64_resized(filepath, scale=0.25):
        img = Image.open(filepath)
        new_size = (img.width // int(1 / scale), img.height // int(1 / scale))
        img = img.resize(new_size, Image.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format='PNG', optimize=True)
        return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()

    NDVI_LAYERS = []
    for name, sensor, years in epochs:
        yr_range = f'{years[0]}-{years[-1]}'
        NDVI_LAYERS.append((f'ndvi_{name}', f'NDVI {yr_range} ({sensor})', True))

    VEG_LAYERS = []
    for name, sensor, years in epochs:
        yr_range = f'{years[0]}-{years[-1]}'
        VEG_LAYERS.append((f'veg_{name}', f'Vegetacao {yr_range}', False))

    EDIF_LAYERS = []
    for name, sensor, years in epochs:
        yr_range = f'{years[0]}-{years[-1]}'
        EDIF_LAYERS.append((f'edif_{name}', f'Edificado {yr_range}', False))

    CHANGE_LAYERS_INFO = [
        ('veg_perda', 'Perda de vegetacao (85-90 → 23-24)', False),
        ('veg_ganho', 'Ganho de vegetacao (85-90 → 23-24)', False),
    ]

    ALL_MAP_LAYERS = (NDVI_LAYERS + VEG_LAYERS + EDIF_LAYERS + CHANGE_LAYERS_INFO
        + [('municipios', 'Limites municipais', True)])

    layers_js_items = []
    for lid, label, show in ALL_MAP_LAYERS:
        b64 = to_base64(os.path.join(layers_dir, f'{lid}.png'))
        layers_js_items.append(
            '{' + f'id:"{lid}",label:"{label}",show:{str(show).lower()},src:"{b64}"' + '}'
        )
    layers_js = ',\n'.join(layers_js_items)

    n_ndvi = len(NDVI_LAYERS)
    n_veg = len(VEG_LAYERS)
    n_edif = len(EDIF_LAYERS)
    n_change = len(CHANGE_LAYERS_INFO)

    layers1947_js_items = []
    for lid, label, color, show in layers_1947:
        b64 = to_base64_resized(os.path.join('1947', 'layers', f'{lid}.png'))
        layers1947_js_items.append(
            '{' + f'id:"{lid}",label:"{label}",color:"{color}",show:{str(show).lower()},src:"{b64}"' + '}'
        )
    layers1947_js = ',\n'.join(layers1947_js_items)

    basemaps = [
        ('CartoDB Dark', 'dark'),
        ('CartoDB Positron', 'positron'),
        ('Ortofoto 1947', 'orto1947'),
        ('Satelite', 'satellite'),
        ('OpenStreetMap', 'osm'),
    ]
    basemap_options = ''.join(
        f'<option value="{key}"{"selected" if key == "positron" else ""}>{name}</option>'
        for i, (name, key) in enumerate(basemaps)
    )

    html = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="icon" type="image/x-icon" href="favicon.ico">
<title>Vegetação do Porto 1947-2024</title>
<meta name="description" content="Mapa histórico da vegetação do Porto de 1947 a 2024, com ortofoto aérea e seis décadas de dados Landsat com normalização inter-sensor.">
<link rel="canonical" href="https://coolio1.github.io/porto_areas_verdes_mudanca/ndvi_historico.html">
<meta property="og:title" content="Vegetação do Porto 1947-2024">
<meta property="og:description" content="Mapa histórico da vegetação do Porto de 1947 a 2024, com ortofoto aérea e dados Landsat.">
<meta property="og:url" content="https://coolio1.github.io/porto_areas_verdes_mudanca/ndvi_historico.html">
<meta property="og:type" content="website">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body { margin:0; }
  #map { position:absolute; top:0; bottom:0; width:100%; }
  #panel {
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(30,30,30,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#eee;
    box-shadow:0 2px 10px rgba(0,0,0,0.5); min-width:320px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }
  .row { display:flex; align-items:center; gap:6px; margin:2px 0; }
  .row input[type=color] { width:22px; height:22px; border:none; cursor:pointer; padding:0; }
  .row input[type=checkbox] { width:15px; height:15px; cursor:pointer; margin:0; }
  .row label { cursor:pointer; font-size:12px; }
  .section { font-size:11px; color:#aaa; font-weight:bold; margin:8px 0 4px 0; }
  select { background:#333; color:#eee; border:1px solid #555; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }
  .swatch { display:inline-block; width:10px; height:10px; border-radius:2px; margin-right:4px; }
  #nav {
    position:fixed; top:10px; right:10px; z-index:1000;
    display:flex; gap:6px; font:11px 'Segoe UI',Arial,sans-serif;
  }
  #nav a {
    background:rgba(255,255,255,0.9); color:#444; text-decoration:none;
    padding:4px 10px; border-radius:5px; box-shadow:0 1px 4px rgba(0,0,0,0.15);
  }
  #nav a:hover { background:#fff; color:#222; }
  #nav a.active { background:#2E7D32; color:#fff; }
</style>
</head>
<body>
<div id="nav">
  <a href="index.html">Início</a>
  <a href="mapa.html">Mapa 2016-2025</a>
  <a href="ndvi_historico.html" class="active">Hist&oacute;rico 1947-2024</a>
  <a href="interiores_quarteiroes.html">Verde Privado</a>
  <a href="acessibilidade/acessibilidade_verde.html">Acessibilidade</a>
  <a href="acessibilidade/conversao_verde.html">Convers&atilde;o</a>
  <a href="atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
  <a href="1947/orto_1947.html">Porto 1947</a>
</div>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Vegetacao do Porto</b><br>
  <span style="color:#aaa;font-size:10px;">1947-2024 &bull; Ortofoto 1947 + Landsat MSS 60m / TM-OLI 30m</span>

  <div class="section">Uso do solo 1947 (Ortofoto)</div>
  <div id="uso1947-rows"></div>

  <div class="section">Mascara de vegetacao por epoca</div>
  <div id="veg-rows"></div>

  <div class="section">Mascara de edificado por epoca</div>
  <div id="edif-rows"></div>

  <div class="section">Perda e ganho (1985-90 vs 2023-24)</div>
  <div id="change-rows"></div>
  <div style="font-size:10px;color:#888;margin:4px 0;">
    <span class="swatch" style="background:#FF4444;"></span>Perda
    <span class="swatch" style="background:#44FF44;margin-left:10px;"></span>Ganho
  </div>

  <div class="section">Outros</div>
  <div id="other-rows"></div>

  <hr style="border-color:#555;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">''' + basemap_options + '''</select>

  <hr style="border-color:#555;margin:10px 0 4px 0;">
  <span style="color:#666;font-size:10px;">
    Fonte: Ortofotomapa 1947 (CIIMAR/FCUP) &bull; Landsat MSS/TM/OLI (USGS/NASA)<br>
    1947: Pixel RF (textura local) &bull; Historico: NDVI &ge; 0.25 &bull; Roy et al. 2016<br>
    Limites: CAOP 2025 (DGT)
  </span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {maxZoom:19, attribution:''}).addTo(map);
var wmsLayer = null;

document.getElementById('basemap-select').addEventListener('change', function() {
  if (baseTile) { map.removeLayer(baseTile); baseTile = null; }
  if (wmsLayer) { map.removeLayer(wmsLayer); wmsLayer = null; }
  var v = this.value;
  if (v === 'orto1947') {
    wmsLayer = L.tileLayer.wms("''' + wms_url + '''", {
      layers: "''' + wms_layer + '''", format: 'image/png', transparent: false,
      version: '1.1.1', maxZoom: 20, attribution: 'CIIMAR/FCUP'
    }).addTo(map);
  } else {
    var urls = {
      dark: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      positron: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
      satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      osm: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
    };
    baseTile = L.tileLayer(urls[v], {maxZoom:19, attribution:''}).addTo(map);
  }
});

// --- 1947 layers (color picker) ---
var bounds1947 = ''' + str(bounds_1947) + ''';
var layers1947 = [''' + layers1947_js + '''];
var overlays1947 = [];

function hexToRgb(h) {
  h = h.replace('#','');
  return [parseInt(h.substring(0,2),16), parseInt(h.substring(2,4),16), parseInt(h.substring(4,6),16)];
}

function extractMask(src) {
  return new Promise(function(r) {
    var i = new Image();
    i.onload = function() {
      var c = document.createElement('canvas');
      c.width = i.width; c.height = i.height;
      var x = c.getContext('2d');
      x.drawImage(i, 0, 0);
      var d = x.getImageData(0, 0, c.width, c.height);
      var a = new Uint8Array(d.data.length / 4);
      for (var j = 0; j < a.length; j++) a[j] = d.data[j * 4 + 3];
      r({w: c.width, h: c.height, alpha: a});
    };
    i.src = src;
  });
}

function renderColored(m, hex) {
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = m.w; c.height = m.h;
  var x = c.getContext('2d');
  var d = x.createImageData(m.w, m.h);
  for (var i = 0; i < m.alpha.length; i++) {
    d.data[i*4] = rgb[0]; d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2]; d.data[i*4+3] = m.alpha[i];
  }
  x.putImageData(d, 0, 0);
  return c.toDataURL();
}

// --- Historico layers ---
var boundsH = ''' + str(bounds) + ''';
var layersH = [''' + layers_js + '''];
var overlaysH = [];
var nNdvi = ''' + str(n_ndvi) + ''';
var nVeg = ''' + str(n_veg) + ''';
var nEdif = ''' + str(n_edif) + ''';
var nChange = ''' + str(n_change) + ''';

function makeCheckbox(container, idx, defaultOn) {
  var row = document.createElement('div');
  row.className = 'row';
  var cb = document.createElement('input');
  cb.type = 'checkbox'; cb.checked = defaultOn; cb.dataset.idx = idx;
  if (defaultOn) overlaysH[idx].addTo(map);
  cb.addEventListener('change', function() {
    var i = +this.dataset.idx;
    if (this.checked) overlaysH[i].addTo(map);
    else map.removeLayer(overlaysH[i]);
  });
  var lb = document.createElement('label');
  lb.textContent = layersH[idx].label;
  row.appendChild(cb);
  row.appendChild(lb);
  container.appendChild(row);
}

async function init() {
  // --- Init 1947 layers ---
  var div1947 = document.getElementById('uso1947-rows');
  for (var i = 0; i < layers1947.length; i++) {
    var L_ = layers1947[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds1947);
    if (L_.show) ov.addTo(map);
    overlays1947.push({overlay: ov, mask: m, color: L_.color, visible: L_.show});

    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {
      var idx = +this.dataset.idx;
      overlays1947[idx].visible = this.checked;
      if (this.checked) overlays1947[idx].overlay.addTo(map);
      else map.removeLayer(overlays1947[idx].overlay);
    });
    var cp = document.createElement('input');
    cp.type = 'color'; cp.value = L_.color; cp.dataset.idx = i;
    cp.addEventListener('input', function() {
      var idx = +this.dataset.idx;
      var s = overlays1947[idx];
      s.color = this.value;
      s.overlay.setUrl(renderColored(s.mask, this.value));
    });
    var lb = document.createElement('label');
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(cp); row.appendChild(lb);
    div1947.appendChild(row);
  }

  // --- Init historico layers ---
  for (var i = 0; i < layersH.length; i++) {
    var ov = L.imageOverlay(layersH[i].src, boundsH);
    overlaysH.push(ov);
  }

  // NDVI checkboxes (exclusive)
  var divNdvi = document.getElementById('ndvi-rows');
  if (divNdvi) {
    for (var i = 0; i < nNdvi; i++) {
      var row = document.createElement('div');
      row.className = 'row';
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = (i === nNdvi - 1); cb.dataset.idx = i;
      if (i === nNdvi - 1) overlaysH[i].addTo(map);
      cb.addEventListener('change', function() {
        var idx = +this.dataset.idx;
        if (this.checked) {
          for (var j = 0; j < nNdvi; j++) {
            if (j !== idx) {
              map.removeLayer(overlaysH[j]);
              divNdvi.querySelectorAll('input[type=checkbox]')[j].checked = false;
            }
          }
          overlaysH[idx].addTo(map);
        } else {
          map.removeLayer(overlaysH[idx]);
        }
      });
      var lb = document.createElement('label');
      lb.textContent = layersH[i].label;
      row.appendChild(cb);
      row.appendChild(lb);
      divNdvi.appendChild(row);
    }
  }

  // Vegetation masks
  var divVeg = document.getElementById('veg-rows');
  for (var i = nNdvi; i < nNdvi + nVeg; i++) {
    makeCheckbox(divVeg, i, false);
  }

  // Edificado masks
  var divEdif = document.getElementById('edif-rows');
  var edifStart = nNdvi + nVeg;
  for (var i = edifStart; i < edifStart + nEdif; i++) {
    makeCheckbox(divEdif, i, false);
  }

  // Change layers (loss/gain)
  var divChange = document.getElementById('change-rows');
  var changeStart = edifStart + nEdif;
  for (var i = changeStart; i < changeStart + nChange; i++) {
    makeCheckbox(divChange, i, false);
  }

  // Other layers (municipios)
  var divOther = document.getElementById('other-rows');
  var otherStart = changeStart + nChange;
  for (var i = otherStart; i < layersH.length; i++) {
    makeCheckbox(divOther, i, layersH[i].show);
  }
}

init();
</script>
<div style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
</body>
</html>'''

    output = os.path.join(script_dir, 'ndvi_historico.html')
    with open(output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\nMapa guardado em {output} ({os.path.getsize(output) // 1024} KB)')
    webbrowser.open(output)
