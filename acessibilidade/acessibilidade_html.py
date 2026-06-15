"""Phase 6 — geração do mapa HTML de acessibilidade a verde público."""

import os
import base64
import json as _json


def to_base64(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def build_html(script_dir, layers_dir, parent_layers, bounds,
               verde_pub_path, verde_pago_path, acc_path, lowpop_path,
               muni_path, prox_path):
    """Gera acessibilidade_verde.html a partir das camadas PNG já calculadas."""
    print("\nA construir mapa...")

    verde_priv_b64 = to_base64(os.path.join(parent_layers, "interior_subsistente.png"))
    verde_pago_b64 = to_base64(verde_pago_path)
    ghspop_b64 = to_base64(os.path.join(parent_layers, "ghspop.png"))
    acc_b64 = to_base64(acc_path)
    lowpop_b64 = to_base64(lowpop_path)
    muni_b64 = to_base64(muni_path)
    prox_b64 = to_base64(prox_path)

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
        print(
            "  AVISO: parques_porto.geojson não encontrado — correr criar_parques.py primeiro"
        )

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
            "Satélite",
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        ),
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
<div id="nav">
  <a href="../index.html">In&iacute;cio</a>
  <a href="../mapa.html">Mapa 2016-2025</a>
  <a href="../ndvi_historico.html">Hist&oacute;rico 1947-2024</a>
  <a href="../interiores_quarteiroes.html">Verde Privado</a>
  <a href="acessibilidade_verde.html" class="active">Acessibilidade</a>
  <a href="../atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <button id="panel-toggle" onclick="var p=document.getElementById('panel');p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'&#9650; Abrir legenda':'&#9660; Fechar';">&#9660; Fechar</button>
  <div class="panel-body">
  <b style="font-size:14px;">Acessibilidade a Verde P&uacute;blico</b>

  <div id="acc-legend" style="display:block;margin:4px 0 8px 0;">
    <div class="section">Acessibilidade (m&sup2;/hab, raio 500m)</div>
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
// Fallback inline (funciona em file://); fetch() actualiza em HTTP (GitHub Pages)
var map = L.map('map').setView([41.155, -8.63], 13);
var parquesData = {parques_geojson_str};

// Em HTTP, recarregar do ficheiro (dados sempre actualizados sem re-gerar HTML)
try {{
  fetch('parques_porto.geojson').then(function(r) {{ return r.json(); }}).then(function(data) {{
    parquesData = data;
    if (typeof initParques === 'function') initParques();
  }}).catch(function() {{}});
}} catch(e) {{}}
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {bounds};

// Camada de acessibilidade (pré-colorida, 70% opacidade, on por defeito)
var accLayer = {{
  id: "acessibilidade",
  label: "Acessibilidade a 500m",
  src: "{acc_b64}",
  opacity: 0.7,
  show: true
}};

// Proximidade 300m (Konijnendijk 3-30-300, pré-colorida)
var proxLayer = {{
  id: "proximidade_300m",
  label: "Proximidade 300m",
  src: "{prox_b64}",
  opacity: 0.7,
  show: false
}};

// Máscara de baixa densidade (cinza claro, topo de tudo)
var lowPopLayer = {{
  id: "baixa_densidade",
  label: "Baixa densidade",
  src: "{lowpop_b64}",
  show: true
}};

// Camada de verde privado (monocromática azul)
var greenPrivLayer = {{
  id: "verde_privado",
  label: "Verde privado",
  color: "#1565C0",
  src: "{verde_priv_b64}",
  show: false
}};

// Camada de verde pago ou não usufruível — castanho
var outroVerdeLayer = {{
  id: "verde_pago",
  label: "Verde em PDM / fechado ao p\\u00fablico",
  color: "#8D6E63",
  src: "{verde_pago_b64}",
  show: false
}};

// Limites municipais
var muniLayer = {{
  id: "municipios",
  label: "Limites municipais",
  color: "#444444",
  src: "{muni_b64}",
  show: true
}};

// Contexto: densidade populacional
var bgLayer = {{
  id: "ghspop",
  label: "Densidade populacional",
  src: "{ghspop_b64}",
  opacity: 0.7,
  show: false
}};

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
  // Pane para camada de fundo (z-index baixo)
  map.createPane('bgPane');
  map.getPane('bgPane').style.zIndex = 250;

  // Pane para acessibilidade (topo)
  map.createPane('accPane');
  map.getPane('accPane').style.zIndex = 450;

  // --- Camada de fundo: densidade pop ---
  var bgOverlay = L.imageOverlay(bgLayer.src, bounds, {{opacity: bgLayer.opacity, pane: 'bgPane'}});
  if (bgLayer.show) bgOverlay.addTo(map);
  var bgDiv = document.getElementById('bg-rows');
  var bgRow = document.createElement('div'); bgRow.className = 'row';
  var bgCb = document.createElement('input'); bgCb.type = 'checkbox'; bgCb.checked = bgLayer.show;
  bgCb.addEventListener('change', function() {{
    if (this.checked) {{ bgOverlay.addTo(map); document.getElementById('pop-legend').style.display='block'; }}
    else {{ map.removeLayer(bgOverlay); document.getElementById('pop-legend').style.display='none'; }}
  }});
  var bgLb = document.createElement('label'); bgLb.textContent = bgLayer.label; bgLb.style.fontSize='12px';
  bgRow.appendChild(bgCb); bgRow.appendChild(bgLb); bgDiv.appendChild(bgRow);

  // --- Camadas principais ---
  var monoLayers = [greenPrivLayer, outroVerdeLayer, muniLayer];
  var div = document.getElementById('layer-rows');
  var overlays = [];

  for (var i = 0; i < monoLayers.length; i++) {{
    var L_ = monoLayers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    overlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) overlays[idx].addTo(map); else map.removeLayer(overlays[idx]);
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    div.appendChild(row);
  }}

  // --- Acessibilidade (topo, pré-colorida) ---
  var accOverlay = L.imageOverlay(accLayer.src, bounds, {{opacity: accLayer.opacity, pane: 'accPane'}});
  if (accLayer.show) accOverlay.addTo(map);

  var accRow = document.createElement('div'); accRow.className = 'row';
  var accCb = document.createElement('input'); accCb.type = 'checkbox'; accCb.checked = accLayer.show;
  accCb.addEventListener('change', function() {{
    if (this.checked) {{
      accOverlay.addTo(map);
      if (window._lowPopOverlay) window._lowPopOverlay.addTo(map);
    }} else {{
      map.removeLayer(accOverlay);
      if (window._lowPopOverlay) map.removeLayer(window._lowPopOverlay);
    }}
  }});
  var accSw = document.createElement('span'); accSw.className = 'swatch';
  accSw.style.background = 'linear-gradient(to right, #880E0E, #B71C1C, #E53935, #E8A838, #FFD700, #8BC34A, #2E7D32)';
  var accLb = document.createElement('label'); accLb.textContent = accLayer.label; accLb.style.fontSize = '12px';
  accRow.appendChild(accCb); accRow.appendChild(accSw); accRow.appendChild(accLb);
  // Acessibilidade no topo
  div.insertBefore(accRow, div.firstChild);

  // --- Proximidade 300m (Konijnendijk 3-30-300, pré-colorida) ---
  var proxOverlay = L.imageOverlay(proxLayer.src, bounds, {{opacity: proxLayer.opacity, pane: 'accPane'}});
  if (proxLayer.show) proxOverlay.addTo(map);

  var proxRow = document.createElement('div'); proxRow.className = 'row';
  var proxCb = document.createElement('input'); proxCb.type = 'checkbox'; proxCb.checked = proxLayer.show;
  proxCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxOverlay.addTo(map);
      if (window._lowPopOverlay) window._lowPopOverlay.addTo(map);
      // Desligar acessibilidade (mutuamente exclusivas)
      accCb.checked = false;
      map.removeLayer(accOverlay);
      document.getElementById('acc-legend').style.display = 'none';
      document.getElementById('prox-legend').style.display = 'block';
    }} else {{
      map.removeLayer(proxOverlay);
      if (window._lowPopOverlay) map.removeLayer(window._lowPopOverlay);
      document.getElementById('prox-legend').style.display = 'none';
    }}
  }});
  // Quando liga acessibilidade, desligar proximidade
  accCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxCb.checked = false;
      map.removeLayer(proxOverlay);
      document.getElementById('prox-legend').style.display = 'none';
      document.getElementById('acc-legend').style.display = 'block';
    }}
  }});
  var proxSw = document.createElement('span'); proxSw.className = 'swatch';
  proxSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  var proxLb = document.createElement('label'); proxLb.textContent = proxLayer.label; proxLb.style.fontSize = '12px';
  proxRow.appendChild(proxCb); proxRow.appendChild(proxSw); proxRow.appendChild(proxLb);
  div.insertBefore(proxRow, accRow.nextSibling);

  // --- Camada "Parques e Jardins" (só polígonos GeoJSON) ---
  map.createPane('parquesPane');
  map.getPane('parquesPane').style.zIndex = 550;

  // Contornos GeoJSON dos parques (carregado via fetch)
  var parquesGeoLayer = null;

  // Checkbox para polígonos
  var pRow = document.createElement('div'); pRow.className = 'row';
  var pCb = document.createElement('input'); pCb.type = 'checkbox'; pCb.checked = true;
  pCb.addEventListener('change', function() {{
    if (this.checked) {{
      if (parquesGeoLayer) parquesGeoLayer.addTo(map);
    }} else {{
      if (parquesGeoLayer) map.removeLayer(parquesGeoLayer);
    }}
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
  var lowPopOverlay = L.imageOverlay(lowPopLayer.src, bounds, {{pane: 'lowPopPane'}});
  window._lowPopOverlay = lowPopOverlay;
  if (accLayer.show) lowPopOverlay.addTo(map);

  // Se os fetch() já terminaram antes de init(), chamar agora
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
