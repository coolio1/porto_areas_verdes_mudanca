"""Phase 6 — geração do mapa HTML de acessibilidade a verde público."""

import os
import sys
import json as _json
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from nav import get_nav


def _make_colored_png(src_path, dst_path, hex_color):
    """Aplica cor sólida à máscara alpha e guarda PNG colorido."""
    if not os.path.exists(src_path):
        return False
    arr = np.array(Image.open(src_path).convert('RGBA'))
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    alpha = arr[:, :, 3].copy()
    arr[:, :, :3] = [r, g, b]
    arr[:, :, 3] = alpha
    Image.fromarray(arr).save(dst_path)
    return True


def _js_src(abs_path, script_dir):
    """Devolve URL relativa para o HTML (com aspas) ou 'null' se ficheiro não existe."""
    if abs_path and os.path.exists(abs_path):
        return "'" + os.path.relpath(abs_path, script_dir).replace(os.sep, '/') + "'"
    return 'null'


def build_html(script_dir, layers_dir, parent_layers, bounds,
               verde_pub_path, verde_pago_path, acc_path, lowpop_path,
               muni_path, prox_path):
    """Gera acessibilidade_verde.html a partir das camadas PNG já calculadas."""
    print("\nA construir mapa...")

    # Gerar PNGs pré-coloridos (evita canvas CORS em file://)
    verde_pago_col = os.path.join(layers_dir, "verde_pago_colored.png")
    _make_colored_png(verde_pago_path, verde_pago_col, "#8D6E63")

    verde_priv_src = os.path.join(parent_layers, "interior_subsistente.png")
    verde_priv_col = os.path.join(parent_layers, "interior_subsistente_colored.png")
    _make_colored_png(verde_priv_src, verde_priv_col, "#1565C0")

    muni_col = os.path.join(parent_layers, "municipios_colored.png")
    _make_colored_png(muni_path, muni_col, "#444444")

    # URLs relativas para o HTML
    acc_js        = _js_src(acc_path,       script_dir)
    prox_js       = _js_src(prox_path,      script_dir)
    lowpop_js     = _js_src(lowpop_path,    script_dir)
    ghspop_js     = _js_src(os.path.join(parent_layers, "ghspop.png"), script_dir)
    verde_pago_js = _js_src(verde_pago_col, script_dir)
    verde_priv_js = _js_src(verde_priv_col, script_dir)
    muni_js       = _js_src(muni_col,       script_dir)

    parques_geojson_path = os.path.join(script_dir, "parques_porto.geojson")
    parques_geojson_str = "null"
    if os.path.exists(parques_geojson_path):
        with open(parques_geojson_path, "r", encoding="utf-8") as f:
            parques_geojson_str = f.read()
        _pdata = _json.loads(parques_geojson_str)
        n_parques = len(_pdata["features"])
        print(f"  Parques nomeados: {n_parques} carregados")
    else:
        n_parques = 0
        print("  AVISO: parques_porto.geojson não encontrado — correr criar_parques.py primeiro")

    basemaps = [
        ("CartoDB Positron", "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"),
        ("CartoDB Dark",     "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
        ("OpenStreetMap",    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"),
        ("Satélite",         "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
    ]
    basemap_options = "".join(
        f'<option value="{url}"{"selected" if i == 0 else ""}>{name}</option>'
        for i, (name, url) in enumerate(basemaps)
    )

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Acessibilidade a Verde P&uacute;blico — Porto</title>
<meta name="description" content="Mapa de acessibilidade da população do Porto a espaços verdes públicos (m²/hab, raio 500m), usando o método 2SFCA com dados GHS-POP e PDM.">
<link rel="canonical" href="https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/acessibilidade_verde.html">
<meta property="og:title" content="Acessibilidade a Verde Público — Porto">
<meta property="og:description" content="Acessibilidade da população a espaços verdes públicos no Porto (m²/hab, raio 500m), método 2SFCA.">
<meta property="og:url" content="https://coolio1.github.io/porto_areas_verdes_mudanca/acessibilidade/acessibilidade_verde.html">
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
  #nav a.active {{ background:#2E7D32; color:#fff; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:260px;
    max-height:90vh; overflow-y:auto; line-height:1.8;
  }}
  #panel-toggle {{
    display:none; width:100%; border:none; padding:6px 0;
    background:transparent; color:#555; font-size:11px; cursor:pointer;
    text-align:right;
  }}
  .panel-body {{ display:block; }}
  .row {{ display:flex; align-items:center; gap:6px; margin:2px 0; }}
  .row input[type=checkbox] {{ width:15px; height:15px; cursor:pointer; margin:0; }}
  .row label {{ cursor:pointer; font-size:12px; }}
  .swatch {{ width:14px; height:14px; border-radius:3px; display:inline-block; }}
  .section {{ font-size:11px; color:#888; font-weight:bold; margin:8px 0 4px 0; }}
  select {{ background:#f5f5f5; color:#222; border:1px solid #ccc; border-radius:4px; padding:3px 6px; font-size:12px; width:100%; }}
  .park-label {{ background:rgba(255,255,255,0.85)!important; border:none!important; box-shadow:0 1px 3px rgba(0,0,0,0.2); font:10px 'Segoe UI',Arial,sans-serif; color:#1B5E20; padding:1px 5px; border-radius:3px; }}
  @media (max-width: 768px) {{
    #panel {{
      left:6px; right:6px; bottom:6px; min-width:unset;
      padding:8px 10px; font-size:11px; line-height:1.3;
      max-height:35vh; overflow-y:auto;
    }}
    #panel b {{ font-size:12px !important; }}
    #panel .section {{ font-size:9px; margin:4px 0 2px; }}
    #panel .row {{ gap:4px; margin:1px 0; }}
    #panel .row input[type=checkbox] {{ width:12px; height:12px; }}
    #panel .row label {{ font-size:10px; }}
    #panel select {{ font-size:10px; padding:2px 4px; }}
    #panel hr {{ margin:4px 0 !important; }}
    #panel .swatch {{ width:10px; height:10px; }}
    #panel.collapsed .panel-body {{ display:none; }}
    #panel-toggle {{ display:block; }}
    #nav {{
      top:4px; right:4px; left:4px;
      flex-wrap:wrap; gap:3px; justify-content:center;
    }}
    #nav a {{ font-size:9px; padding:2px 6px; }}
    .leaflet-top {{ top:50px; }}
    #credit {{ display:none; }}
  }}
</style>
</head>
<body>
{get_nav('acessibilidade/acessibilidade_verde.html', depth=1)}
<div id="map"></div>
<div id="panel">
  <button id="panel-toggle" onclick="var p=document.getElementById('panel');p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'&#9650; Abrir legenda':'&#9660; Fechar';">&#9660; Fechar</button>
  <div class="panel-body">
  <b style="font-size:14px;">Acessibilidade a Verde P&uacute;blico</b>

  <div id="acc-legend" style="display:block;margin:4px 0 8px 0;">
    <div class="section">Acessibilidade 500m (m&sup2;/hab)</div>
    <div style="font-size:10px;color:#888;margin-bottom:2px;">m&sup2;/hab (raio 500m)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">0 &ndash; 3 (d&eacute;fice cr&iacute;tico)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#E8A838;display:inline-block;"></span>
        <span style="color:#666;">3 &ndash; 9 (insuficiente)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">&gt;9 (adequado)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;margin-top:2px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#C8C8C8;display:inline-block;"></span>
        <span style="color:#666;">Baixa densidade</span>
      </div>
    </div>
    <div style="color:#aaa;font-size:9px;margin-top:4px;">OMS recomenda &ge;9 m&sup2;/hab</div>
  </div>

  <div id="prox-legend" style="display:none;margin:4px 0 8px 0;">
    <div class="section">Proximidade 300m (Konijnendijk 3-30-300)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">&le;300m de parque &ge;0,4 ha (cumpre)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">&gt;300m de parque &ge;0,4 ha (n&atilde;o cumpre)</span>
      </div>
    </div>
    <div style="color:#aaa;font-size:9px;margin-top:4px;">OMS: &ge;0,4 ha de verde a &lt;300m de casa</div>
  </div>

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
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; GHS-POP 100m (JRC)<br>
  {n_parques} parques e jardins (CMP + OSM)<br>
  M&eacute;todo: Two-Step Floating Catchment Area</span>
  </div>
</div>

<script>
var map = L.map('map').setView([41.155, -8.63], 13);
var parquesData = {parques_geojson_str};
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {bounds};

var accLayer = {{
  id: "acessibilidade",
  label: "Acessibilidade 500m",
  src: {acc_js},
  opacity: 0.7,
  show: true
}};

var proxLayer = {{
  id: "proximidade_300m",
  label: "Proximidade 300m",
  src: {prox_js},
  opacity: 0.7,
  show: false
}};

var lowPopLayer = {{
  id: "baixa_densidade",
  label: "Baixa densidade",
  src: {lowpop_js},
  show: true
}};

var greenPrivLayer = {{
  id: "verde_privado",
  label: "Verde privado",
  color: "#1565C0",
  src: {verde_priv_js},
  show: false
}};

var outroVerdeLayer = {{
  id: "verde_pago",
  label: "Verde em PDM / fechado ao p\\u00fablico",
  color: "#8D6E63",
  src: {verde_pago_js},
  show: false
}};

var muniLayer = {{
  id: "municipios",
  label: "Limites municipais",
  color: "#444444",
  src: {muni_js},
  show: true
}};

var bgLayer = {{
  id: "ghspop",
  label: "Densidade populacional",
  src: {ghspop_js},
  opacity: 0.7,
  show: false
}};

function init() {{
  map.createPane('bgPane');
  map.getPane('bgPane').style.zIndex = 250;

  map.createPane('accPane');
  map.getPane('accPane').style.zIndex = 450;

  // --- Camada de fundo: densidade pop ---
  var bgOverlay = bgLayer.src ? L.imageOverlay(bgLayer.src, bounds, {{opacity: bgLayer.opacity, pane: 'bgPane'}}) : null;
  if (bgOverlay && bgLayer.show) bgOverlay.addTo(map);
  var bgDiv = document.getElementById('bg-rows');
  var bgRow = document.createElement('div'); bgRow.className = 'row';
  var bgCb = document.createElement('input'); bgCb.type = 'checkbox'; bgCb.checked = bgLayer.show;
  bgCb.addEventListener('change', function() {{
    if (this.checked) {{
      if (bgOverlay) bgOverlay.addTo(map);
      document.getElementById('pop-legend').style.display = 'block';
    }} else {{
      if (bgOverlay) map.removeLayer(bgOverlay);
      document.getElementById('pop-legend').style.display = 'none';
    }}
  }});
  var bgLb = document.createElement('label'); bgLb.textContent = bgLayer.label; bgLb.style.fontSize = '12px';
  bgRow.appendChild(bgCb); bgRow.appendChild(bgLb); bgDiv.appendChild(bgRow);

  // --- Camadas principais (pré-coloridas em Python) ---
  var monoLayers = [greenPrivLayer, outroVerdeLayer, muniLayer];
  var div = document.getElementById('layer-rows');
  var overlays = [];

  for (var i = 0; i < monoLayers.length; i++) {{
    var L_ = monoLayers[i];
    var ov = L_.src ? L.imageOverlay(L_.src, bounds) : null;
    if (ov && L_.show) ov.addTo(map);
    overlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) {{ if (overlays[idx]) overlays[idx].addTo(map); }}
      else {{ if (overlays[idx]) map.removeLayer(overlays[idx]); }}
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    div.appendChild(row);
  }}

  // --- Acessibilidade (pré-colorida, topo) ---
  var accOverlay = accLayer.src ? L.imageOverlay(accLayer.src, bounds, {{opacity: accLayer.opacity, pane: 'accPane'}}) : null;
  if (accOverlay && accLayer.show) accOverlay.addTo(map);

  var accRow = document.createElement('div'); accRow.className = 'row';
  var accCb = document.createElement('input'); accCb.type = 'checkbox'; accCb.checked = accLayer.show;
  accCb.addEventListener('change', function() {{
    if (this.checked) {{
      if (accOverlay) accOverlay.addTo(map);
      if (window._lowPopOverlay) window._lowPopOverlay.addTo(map);
    }} else {{
      if (accOverlay) map.removeLayer(accOverlay);
      if (window._lowPopOverlay) map.removeLayer(window._lowPopOverlay);
    }}
  }});
  var accSw = document.createElement('span'); accSw.className = 'swatch';
  accSw.style.background = 'linear-gradient(to right, #880E0E, #B71C1C, #E53935, #E8A838, #FFD700, #8BC34A, #2E7D32)';
  var accLb = document.createElement('label'); accLb.textContent = accLayer.label; accLb.style.fontSize = '12px';
  accRow.appendChild(accCb); accRow.appendChild(accSw); accRow.appendChild(accLb);
  div.insertBefore(accRow, div.firstChild);

  // --- Proximidade 300m (Konijnendijk 3-30-300) ---
  var proxOverlay = proxLayer.src ? L.imageOverlay(proxLayer.src, bounds, {{opacity: proxLayer.opacity, pane: 'accPane'}}) : null;
  if (proxOverlay && proxLayer.show) proxOverlay.addTo(map);

  var proxRow = document.createElement('div'); proxRow.className = 'row';
  var proxCb = document.createElement('input'); proxCb.type = 'checkbox'; proxCb.checked = proxLayer.show;
  proxCb.addEventListener('change', function() {{
    if (this.checked) {{
      if (proxOverlay) proxOverlay.addTo(map);
      if (window._lowPopOverlay) window._lowPopOverlay.addTo(map);
      accCb.checked = false;
      if (accOverlay) map.removeLayer(accOverlay);
      document.getElementById('acc-legend').style.display = 'none';
      document.getElementById('prox-legend').style.display = 'block';
    }} else {{
      if (proxOverlay) map.removeLayer(proxOverlay);
      if (window._lowPopOverlay) map.removeLayer(window._lowPopOverlay);
      document.getElementById('prox-legend').style.display = 'none';
    }}
  }});
  accCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxCb.checked = false;
      if (proxOverlay) map.removeLayer(proxOverlay);
      document.getElementById('prox-legend').style.display = 'none';
      document.getElementById('acc-legend').style.display = 'block';
    }}
  }});
  var proxSw = document.createElement('span'); proxSw.className = 'swatch';
  proxSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  var proxLb = document.createElement('label'); proxLb.textContent = proxLayer.label; proxLb.style.fontSize = '12px';
  proxRow.appendChild(proxCb); proxRow.appendChild(proxSw); proxRow.appendChild(proxLb);
  div.insertBefore(proxRow, accRow.nextSibling);

  // --- Parques e Jardins (GeoJSON) ---
  map.createPane('parquesPane');
  map.getPane('parquesPane').style.zIndex = 550;

  var parquesGeoLayer = null;

  var pRow = document.createElement('div'); pRow.className = 'row';
  var pCb = document.createElement('input'); pCb.type = 'checkbox'; pCb.checked = true;
  pCb.addEventListener('change', function() {{
    if (this.checked) {{ if (parquesGeoLayer) parquesGeoLayer.addTo(map); }}
    else {{ if (parquesGeoLayer) map.removeLayer(parquesGeoLayer); }}
  }});
  var pSw = document.createElement('span'); pSw.className = 'swatch'; pSw.style.backgroundColor = '#2E7D32';
  var pLb = document.createElement('label'); pLb.textContent = 'Parques e Jardins'; pLb.style.fontSize = '12px';
  pRow.appendChild(pCb); pRow.appendChild(pSw); pRow.appendChild(pLb);
  div.insertBefore(pRow, proxRow.nextSibling);

  window.initParques = function() {{
    if (!parquesData) return;
    parquesGeoLayer = L.geoJson(parquesData, {{
      pane: 'parquesPane',
      style: function(f) {{
        return {{
          color: '#1B5E20', weight: 2.5, opacity: 0.9,
          fillColor: '#2E7D32', fillOpacity: 0.45
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var area = p.area_calc_ha ? p.area_calc_ha + ' ha' : '';
        var html = '<b style="font-size:13px;">' + p.nome + '</b><br>';
        html += '<span style="color:#666;">' + (p.tipo || '') + (area ? ' &mdash; ' + area : '') + '</span>';
        layer.bindPopup(html);
        layer.bindTooltip(p.nome, {{
          permanent: true, direction: 'center',
          className: 'park-label',
          offset: [0, 0]
        }});
      }}
    }});
    if (pCb.checked) parquesGeoLayer.addTo(map);
    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.park-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 14 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }};

  // --- Baixa densidade (acima da acessibilidade, abaixo dos parques) ---
  map.createPane('lowPopPane');
  map.getPane('lowPopPane').style.zIndex = 475;
  var lowPopOverlay = lowPopLayer.src ? L.imageOverlay(lowPopLayer.src, bounds, {{pane: 'lowPopPane'}}) : null;
  window._lowPopOverlay = lowPopOverlay;
  if (lowPopOverlay && accLayer.show) lowPopOverlay.addTo(map);

  if (parquesData) initParques();
}}

init();
</script>
<div id="credit" style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
<script>if(window.innerWidth<=768){{var p=document.getElementById('panel'),b=document.getElementById('panel-toggle');p.classList.add('collapsed');b.textContent='\\u25B2 Abrir legenda';}}</script>
</body>
</html>'''

    output = os.path.join(script_dir, "acessibilidade_verde.html")
    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nMapa guardado: {output}")
    print(f"Abrir no browser: file:///{output.replace(os.sep, '/')}")
