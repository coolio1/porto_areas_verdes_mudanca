"""Gera conversao_verde.html a partir das layers de candidatos a conversao."""
import base64
import json
import os


def build_html(script_dir, layers_dir, parent_layers_dir, geojson, pct_actual, pct, target_pct, bounds):
    """Constroi mapa HTML de candidatos a conversao e escreve para script_dir."""

    def to_base64(filepath):
        with open(filepath, "rb") as fh:
            return "data:image/png;base64," + base64.b64encode(fh.read()).decode()

    cand_b64 = to_base64(os.path.join(layers_dir, "candidatos_conversao.png"))
    prox_sim_b64 = to_base64(os.path.join(layers_dir, "proximidade_simulada.png"))
    prox_actual_b64 = to_base64(os.path.join(layers_dir, "proximidade_300m.png"))
    verde_pub_b64 = to_base64(os.path.join(layers_dir, "verde_publico.png"))
    lowpop_b64 = to_base64(os.path.join(layers_dir, "baixa_densidade.png"))
    muni_b64 = to_base64(os.path.join(parent_layers_dir, "municipios.png"))

    geojson_str = json.dumps(geojson, ensure_ascii=False)

    parques_geojson_str = "null"
    parques_path_gj = os.path.join(script_dir, "parques_porto.geojson")
    if os.path.exists(parques_path_gj):
        with open(parques_path_gj, "r", encoding="utf-8") as fh:
            parques_geojson_str = fh.read()

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
<title>Candidatos a Convers&atilde;o de Verde &mdash; Porto</title>
<meta name="description" content="Simula&ccedil;&atilde;o sequencial de espa&ccedil;os verdes que podem colmatar o d&eacute;fice de proximidade (300m) no Porto.">
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
  #nav a.active {{ background:#00897B; color:#fff; }}
  #panel {{
    position:fixed; bottom:20px; left:20px; z-index:1000;
    background:rgba(255,255,255,0.95); padding:14px 18px; border-radius:10px;
    font:13px 'Segoe UI',Arial,sans-serif; color:#222;
    box-shadow:0 2px 10px rgba(0,0,0,0.2); min-width:280px;
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
  .cand-label {{ background:rgba(255,255,255,0.9)!important; border:none!important; box-shadow:0 1px 3px rgba(0,0,0,0.2); font:10px 'Segoe UI',Arial,sans-serif; color:#00695C; padding:1px 5px; border-radius:3px; font-weight:bold; }}
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
  <a href="acessibilidade_verde.html">Acessibilidade</a>
  <a href="conversao_verde.html" class="active">Convers&atilde;o</a>
  <a href="../atropelamentos/dashboard_atropelamentos.html">Atropelamentos</a>
</div>
<div id="map"></div>
<div id="panel">
  <button id="panel-toggle" onclick="var p=document.getElementById('panel');p.classList.toggle('collapsed');this.textContent=p.classList.contains('collapsed')?'&#9650; Abrir legenda':'&#9660; Fechar';">&#9660; Fechar</button>
  <div class="panel-body">
  <b style="font-size:14px;">Candidatos a Convers&atilde;o</b>
  <div style="color:#666;font-size:10px;margin:2px 0 6px;">Simula&ccedil;&atilde;o sequencial para atingir {target_pct:.0f}% de cobertura a &le;300m (Konijnendijk)</div>

  <div style="margin:4px 0 8px 0;">
    <div class="section">Candidatos (por prioridade)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#00897B;display:inline-block;"></span>
        <span style="color:#666;">Estrat&eacute;gia de expans&atilde;o (CMP)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#8D6E63;display:inline-block;"></span>
        <span style="color:#666;">Verde pago ou n&atilde;o usufru&iacute;vel</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#1565C0;display:inline-block;"></span>
        <span style="color:#666;">Verde privado</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#FF8F00;display:inline-block;"></span>
        <span style="color:#666;">Parques e Jardins j&aacute; existentes</span>
      </div>
    </div>
    <div class="section" style="margin-top:6px;">Proximidade 300m (Konijnendijk)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">&le;300m de parque &ge;0,5 ha (cumpre)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">&gt;300m de parque &ge;0,5 ha (n&atilde;o cumpre)</span>
      </div>
    </div>
    <div style="color:#aaa;font-size:9px;margin-top:4px;">Cobertura actual: {pct_actual:.1f}% &rarr; objectivo: {target_pct:.0f}%</div>
  </div>

  <div class="section">Camadas</div>
  <div id="layer-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Contexto</div>
  <div id="ctx-rows"></div>

  <hr style="border-color:#ddd;margin:10px 0 6px 0;">
  <div class="section">Fundo</div>
  <select id="basemap-select">{basemap_options}</select>

  <hr style="border-color:#ddd;margin:10px 0 4px 0;">
  <span style="color:#aaa;font-size:10px;">Sentinel-2 10m (ESA) &bull; GHS-POP 100m (JRC)<br>
  Crit&eacute;rio: Konijnendijk 3-30-300 (&ge;0,5 ha a &le;300m)</span>
  </div>
</div>

<script>
var candidatosData = {geojson_str};
var parquesData = {parques_geojson_str};
var map = L.map('map').setView([41.155, -8.63], 13);

fetch('parques_porto.geojson').then(function(r) {{ return r.json(); }}).then(function(data) {{
  parquesData = data;
  if (typeof initParques === 'function') initParques();
}}).catch(function() {{}});
var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {bounds};

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
  map.createPane('proxPane');
  map.getPane('proxPane').style.zIndex = 350;
  map.createPane('lowPopPane');
  map.getPane('lowPopPane').style.zIndex = 375;
  map.createPane('candPane');
  map.getPane('candPane').style.zIndex = 450;
  map.createPane('parquesPane');
  map.getPane('parquesPane').style.zIndex = 500;
  map.createPane('candGeoPane');
  map.getPane('candGeoPane').style.zIndex = 550;

  var div = document.getElementById('layer-rows');
  var ctxDiv = document.getElementById('ctx-rows');

  // --- Candidatos raster ---
  var candOverlay = L.imageOverlay("{cand_b64}", bounds, {{opacity: 0.85, pane: 'candPane'}});
  candOverlay.addTo(map);

  // --- Candidatos GeoJSON (contornos + popups) ---
  var candGeoLayer = null;
  if (candidatosData && candidatosData.features.length > 0) {{
    var tipoColors = {{
      'Estrategia de expansao (CMP)': '#00897B',
      'Verde pago ou nao usufruivel': '#8D6E63',
      'Verde privado': '#1565C0',
      'Parques e Jardins ja existentes': '#FF8F00',
      'Parques e Jardins já existentes': '#FF8F00'
    }};
    candGeoLayer = L.geoJson(candidatosData, {{
      pane: 'candGeoPane',
      style: function(f) {{
        var color = tipoColors[f.properties.tipo] || '#888';
        return {{
          color: color, weight: 2.5, opacity: 0.9,
          fillColor: color, fillOpacity: 0.55
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var html = '<b style="font-size:13px;">#' + p.rank + '</b>';
        if (p.nome) html += ' &mdash; ' + p.nome;
        html += '<br><span style="color:#666;">' + p.tipo + '</span>';
        html += '<br><span style="color:#666;">&Aacute;rea: ' + p.area_ha + ' ha</span>';
        html += '<br><span style="color:#2E7D32;">+' + p.pop_delta.toLocaleString() + ' hab cobertos</span>';
        html += '<br><span style="color:#444;">Cobertura: ' + p.pct_antes + '% &rarr; ' + p.pct_depois + '%</span>';
        layer.bindPopup(html);
        var label = '#' + p.rank + (p.nome ? ' — ' + p.nome : '');
        layer.bindTooltip(label, {{
          permanent: true, direction: 'center',
          className: 'cand-label',
          offset: [0, 0]
        }});
        if (p.label_lat && p.label_lon) {{
          layer.on('tooltipopen', function() {{
            layer.getTooltip().setLatLng([p.label_lat, p.label_lon]);
          }});
        }}
      }}
    }});
    candGeoLayer.addTo(map);

    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.cand-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 13 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }}

  // Checkbox candidatos
  var cRow = document.createElement('div'); cRow.className = 'row';
  var cCb = document.createElement('input'); cCb.type = 'checkbox'; cCb.checked = true;
  cCb.addEventListener('change', function() {{
    if (this.checked) {{
      candOverlay.addTo(map);
      if (candGeoLayer) candGeoLayer.addTo(map);
    }} else {{
      map.removeLayer(candOverlay);
      if (candGeoLayer) map.removeLayer(candGeoLayer);
    }}
  }});
  var cSw = document.createElement('span'); cSw.className = 'swatch';
  cSw.style.background = 'linear-gradient(135deg, #00897B 25%, #8D6E63 50%, #1565C0 75%, #FF8F00 100%)';
  var cLb = document.createElement('label'); cLb.textContent = 'Candidatos a convers\\u00e3o'; cLb.style.fontSize = '12px';
  cRow.appendChild(cCb); cRow.appendChild(cSw); cRow.appendChild(cLb);
  div.appendChild(cRow);

  // --- Proximidade simulada (com candidatos implementados) ---
  var proxSimOverlay = L.imageOverlay("{prox_sim_b64}", bounds, {{opacity: 0.7, pane: 'proxPane'}});
  proxSimOverlay.addTo(map);

  var lowPopOverlay = L.imageOverlay("{lowpop_b64}", bounds, {{pane: 'lowPopPane'}});
  lowPopOverlay.addTo(map);

  // Proximidade actual (para comparação)
  var proxActualOverlay = L.imageOverlay("{prox_actual_b64}", bounds, {{opacity: 0.7, pane: 'proxPane'}});

  var proxSimRow = document.createElement('div'); proxSimRow.className = 'row';
  var proxSimCb = document.createElement('input'); proxSimCb.type = 'checkbox'; proxSimCb.checked = true;
  proxSimCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxSimOverlay.addTo(map); lowPopOverlay.addTo(map);
    }} else {{
      map.removeLayer(proxSimOverlay); map.removeLayer(lowPopOverlay);
    }}
  }});
  var proxSimSw = document.createElement('span'); proxSimSw.className = 'swatch';
  proxSimSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  var proxSimLb = document.createElement('label'); proxSimLb.textContent = 'Proximidade simulada ({pct:.0f}%)'; proxSimLb.style.fontSize = '12px';
  proxSimRow.appendChild(proxSimCb); proxSimRow.appendChild(proxSimSw); proxSimRow.appendChild(proxSimLb);
  div.appendChild(proxSimRow);

  var proxActRow = document.createElement('div'); proxActRow.className = 'row';
  var proxActCb = document.createElement('input'); proxActCb.type = 'checkbox'; proxActCb.checked = false;
  proxActCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxActualOverlay.addTo(map);
      proxSimCb.checked = false; map.removeLayer(proxSimOverlay);
    }} else {{
      map.removeLayer(proxActualOverlay);
    }}
  }});
  proxSimCb.addEventListener('change', function() {{
    if (this.checked) {{
      proxActCb.checked = false; map.removeLayer(proxActualOverlay);
    }}
  }});
  var proxActSw = document.createElement('span'); proxActSw.className = 'swatch';
  proxActSw.style.background = 'linear-gradient(to right, #B71C1C, #2E7D32)';
  proxActSw.style.opacity = '0.5';
  var proxActLb = document.createElement('label'); proxActLb.textContent = 'Proximidade actual ({pct_actual:.0f}%)'; proxActLb.style.fontSize = '12px';
  proxActRow.appendChild(proxActCb); proxActRow.appendChild(proxActSw); proxActRow.appendChild(proxActLb);
  div.appendChild(proxActRow);

  // --- Contexto: parques, municipios ---
  var ctxLayers = [
    {{ id: "verde_publico", label: "Parques e Jardins", color: "#2E7D32", src: "{verde_pub_b64}", show: false }},
    {{ id: "municipios", label: "Limites municipais", color: "#444444", src: "{muni_b64}", show: true }},
  ];
  var ctxOverlays = [];

  for (var i = 0; i < ctxLayers.length; i++) {{
    var L_ = ctxLayers[i];
    var m = await extractMask(L_.src);
    var cs = renderColored(m, L_.color);
    var ov = L.imageOverlay(cs, bounds);
    if (L_.show) ov.addTo(map);
    ctxOverlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      if (this.checked) ctxOverlays[idx].addTo(map); else map.removeLayer(ctxOverlays[idx]);
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    ctxDiv.appendChild(row);
  }}

  // --- Parques GeoJSON (contornos, contexto) — carregado via fetch ---
  window.initParques = function() {{
    if (!parquesData) return;
    var parquesGeoLayer = L.geoJson(parquesData, {{
      pane: 'parquesPane',
      style: function() {{
        return {{
          color: '#1B5E20', weight: 1.5, opacity: 0.6,
          fillColor: '#2E7D32', fillOpacity: 0.03,
          dashArray: '3 3'
        }};
      }},
      onEachFeature: function(f, layer) {{
        layer.bindTooltip(f.properties.nome, {{
          permanent: true, direction: 'center',
          className: 'park-label',
          offset: [0, 0]
        }});
      }}
    }});
    parquesGeoLayer.addTo(map);

    map.on('zoomend', function() {{
      var labels = document.querySelectorAll('.park-label');
      var z = map.getZoom();
      labels.forEach(function(l) {{ l.style.display = z >= 15 ? '' : 'none'; }});
    }});
    map.fire('zoomend');
  }};

  // Se o fetch() já terminou antes de init(), chamar agora
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

    output_path = os.path.join(script_dir, "conversao_verde.html")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"\nMapa gerado: {output_path}")
    print(f"  Tamanho: {os.path.getsize(output_path) // 1024} KB")
    print("\nConcluido.")
