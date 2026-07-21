"""Gera interiores_quarteiroes.html a partir das camadas PNG já calculadas."""
import base64
import os
import webbrowser


def build_html(script_dir, layers_dir, bounds):
    """Constrói mapa HTML do verde privado e escreve para script_dir."""

    def to_base64(filepath):
        with open(filepath, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode()

    BACKGROUND_LAYER = (
        "ghspop",
        "Densidade populacional",
        to_base64(os.path.join(layers_dir, "ghspop.png")),
        0.7,
        False,
    )

    MAP_LAYERS = [
        ("interior_subsistente", "Subsistente", "#2E7D32", True),
        ("interior_perdido", "Perdido (2016-2025)", "#D7263D", True),
        ("centro_alargado", "Interior VCI", "#FFD700", True),
        ("municipios", "Limites municipais", "#444444", True),
    ]

    layers_js_items = []
    for lid, label, color, show in MAP_LAYERS:
        b64 = to_base64(os.path.join(layers_dir, f"{lid}.png"))
        layers_js_items.append(
            f'{{id:"{lid}",label:"{label}",color:"{color}",show:{str(show).lower()},src:"{b64}"}}'
        )
    layers_js = ",\n".join(layers_js_items)

    bg_id, bg_label, bg_src, bg_opacity, bg_show = BACKGROUND_LAYER
    bg_js = f'{{id:"{bg_id}",label:"{bg_label}",opacity:{bg_opacity},show:{str(bg_show).lower()},src:"{bg_src}"}}'

    basemaps = [
        (
            "CartoDB Positron",
            "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        ),
        ("CartoDB Dark", "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
        (
            "OpenStreetMap",
            "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        ),
        (
            "Satelite",
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ),
    ]
    basemap_options = "".join(
        f'<option value="{url}"{"selected" if i == 0 else ""}>{name}</option>'
        for i, (name, url) in enumerate(basemaps)
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="icon" type="image/x-icon" href="favicon.ico">
<title>Verde Privado — Porto</title>
<meta name="description" content="Mapa dos espaços verdes privados encravados no tecido urbano do Porto: os que subsistem e os que foram perdidos (Sentinel-2 + PDM).">
<link rel="canonical" href="https://portoverde.pt/interiores/interiores_quarteiroes.html">
<meta property="og:title" content="Verde Privado — Porto">
<meta property="og:description" content="Espaços verdes privados encravados no tecido urbano do Porto: os que subsistem e os que foram perdidos.">
<meta property="og:url" content="https://portoverde.pt/interiores/interiores_quarteiroes.html">
<meta property="og:type" content="website">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body {{ margin:0; }}
  #map {{ position:absolute; top:0; bottom:0; width:100%; }}
  #nav {{
    position:fixed; top:10px; right:10px; z-index:1000;
    display:flex; gap:6px; font:11px 'Segoe UI',Arial,sans-serif;
  }}
  #nav a {{
    background:rgba(255,255,255,0.9); color:#444; text-decoration:none;
    padding:4px 10px; border-radius:5px; box-shadow:0 1px 4px rgba(0,0,0,0.15);
  }}
  #nav a:hover {{ background:#fff; color:#222; }}
  #nav a.active {{ background:var(--green,#2E7D32); color:#fff; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:260px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }}
  .row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; margin:0; }}
  .row label {{ cursor:pointer; }}
  .swatch {{ width:14px; height:14px; border-radius:3px; display:inline-block; }}
  .section {{ font-size:11px; color:#888; font-weight:bold; margin:8px 0 4px 0; }}
  select {{ background:#f5f5f5; color:#222; border:1px solid #ccc; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }}
</style>
</head>
<body>
<div id="nav">
  <a href="index.html">In&iacute;cio</a>
  <a href="mapa.html">Mapa 2016-2025</a>
  <a href="ndvi_historico.html">Hist&oacute;rico 1947-2024</a>
  <a href="interiores_quarteiroes.html" class="active">Verde Privado</a>
  <a href="acessibilidade/acessibilidade_verde.html">Acessibilidade</a>
  <a href="acessibilidade/conversao_verde.html">Convers&atilde;o</a>
  <a href="atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
  <a href="1947/orto_1947.html">Porto 1947</a>
</div>
<div id="map"></div>
<div id="panel">
  <b style="font-size:14px;">Verde Privado</b><br>
  <span style="color:#888;font-size:10px;">Espa&ccedil;os verdes privados encravados no tecido urbano</span>

  <div class="section">Camadas</div>
  <div id="layer-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Contexto</div>
  <div id="bg-rows"></div>
  <div id="pop-legend" style="display:none;margin:4px 0 0 22px;">
    <div style="font-size:10px;color:#888;margin-bottom:2px;">hab/pixel (100m)</div>
    <div style="display:flex;align-items:center;gap:4px;">
      <span style="font-size:9px;color:#888;">0</span>
      <div style="width:120px;height:10px;border-radius:3px;background:linear-gradient(to right,#f5e6d0,#d4b896,#b08a5e,#8b6934,#6b4a1e,#4a2f0a);"></div>
      <span style="font-size:9px;color:#888;">150+</span>
    </div>
  </div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#ddd;margin:10px 0 4px 0;">
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; 2016-17 vs 2024-25<br>Parques exclu&iacute;dos via OpenStreetMap</span>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {bounds};
var bgLayer = {bg_js};
var layers = [{layers_js}];
var state = [];
var bgOverlay = null;

function hexToRgb(h) {{
  h = h.replace('#','');
  return [parseInt(h.substr(0,2),16), parseInt(h.substr(2,2),16), parseInt(h.substr(4,2),16)];
}}

function extractMask(src) {{
  return new Promise(function(r) {{
    var i = new Image();
    i.onload = function() {{
      var c = document.createElement('canvas');
      c.width = i.width; c.height = i.height;
      var x = c.getContext('2d');
      x.drawImage(i, 0, 0);
      var d = x.getImageData(0, 0, c.width, c.height);
      var a = new Uint8Array(d.data.length / 4);
      for (var j = 0; j < a.length; j++) a[j] = d.data[j * 4 + 3];
      r({{w: c.width, h: c.height, alpha: a}});
    }};
    i.src = src;
  }});
}}

function renderColored(m, hex) {{
  var rgb = hexToRgb(hex);
  var c = document.createElement('canvas');
  c.width = m.w; c.height = m.h;
  var x = c.getContext('2d');
  var d = x.createImageData(m.w, m.h);
  for (var i = 0; i < m.alpha.length; i++) {{
    d.data[i*4] = rgb[0]; d.data[i*4+1] = rgb[1];
    d.data[i*4+2] = rgb[2]; d.data[i*4+3] = m.alpha[i];
  }}
  x.putImageData(d, 0, 0);
  return c.toDataURL();
}}

async function init() {{
  // Pane dedicado para camada de fundo (z-index abaixo do overlay padrao)
  map.createPane('bgPane');
  map.getPane('bgPane').style.zIndex = 250;
  bgOverlay = L.imageOverlay(bgLayer.src, bounds, {{opacity: bgLayer.opacity, pane: 'bgPane'}});
  if (bgLayer.show) bgOverlay.addTo(map);
  var bgDiv = document.getElementById('bg-rows');
  var bgRow = document.createElement('div');
  bgRow.className = 'row';
  var bgCb = document.createElement('input');
  bgCb.type = 'checkbox'; bgCb.checked = bgLayer.show;
  bgCb.addEventListener('change', function() {{
    if (this.checked) {{ bgOverlay.addTo(map); document.getElementById('pop-legend').style.display='block'; }}
    else {{ map.removeLayer(bgOverlay); document.getElementById('pop-legend').style.display='none'; }}
  }});
  var bgLb = document.createElement('label');
  bgLb.textContent = bgLayer.label;
  bgLb.style.fontSize = '12px';
  bgRow.appendChild(bgCb);
  bgRow.appendChild(bgLb);
  bgDiv.appendChild(bgRow);

  // Camadas principais
  var div = document.getElementById('layer-rows');
  for (var i = 0; i < layers.length; i++) {{
    var L_ = layers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    state.push({{overlay: ov, mask: m, color: L_.color}});

    var row = document.createElement('div');
    row.className = 'row';

    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) state[idx].overlay.addTo(map);
      else map.removeLayer(state[idx].overlay);
    }});

    var sw = document.createElement('span');
    sw.className = 'swatch';
    sw.style.backgroundColor = L_.color;

    var lb = document.createElement('label');
    lb.textContent = L_.label;
    lb.style.fontSize = '12px';

    row.appendChild(cb);
    row.appendChild(sw);
    row.appendChild(lb);
    div.appendChild(row);
  }}
}}

init();
</script>
<div style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
</body>
</html>"""

    output = os.path.join(script_dir, "interiores_quarteiroes.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nMapa guardado em {output} ({os.path.getsize(output) // 1024} KB)")
    webbrowser.open(output)
