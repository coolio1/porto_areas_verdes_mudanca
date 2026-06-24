"""Gera conversao_verde.html a partir das layers de candidatos a conversao."""
import json
import os
import sys

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


def build_html(script_dir, layers_dir, parent_layers_dir, geojson, pct_actual, pct, target_pct, bounds,
               sfca_actual_pct=None, sfca_sim_pct=None):
    """Constroi mapa HTML de candidatos a conversao e escreve para script_dir."""

    # PNGs coloridos para camadas de contexto (sem extracção de máscara via canvas)
    _make_colored_png(
        os.path.join(parent_layers_dir, "municipios.png"),
        os.path.join(parent_layers_dir, "municipios_colored.png"),
        "#444444"
    )

    if pct_actual is None or pct is None:
        raise ValueError("pct_actual e pct são obrigatórios para gerar o mapa de conversão")

    sfca_actual_label = f"{sfca_actual_pct:.1f}%" if sfca_actual_pct is not None else "actual"
    sfca_sim_label    = f"{sfca_sim_pct:.1f}%"    if sfca_sim_pct    is not None else "simulado"

    geojson_str = json.dumps(geojson, ensure_ascii=False)

    parques_geojson_str = "null"
    parques_path = os.path.join(script_dir, "parques_porto.geojson")
    if os.path.exists(parques_path):
        with open(parques_path, "r", encoding="utf-8") as _f:
            parques_geojson_str = _f.read()

    def js_path(abs_path, rel_url):
        return f"'{rel_url}'" if os.path.exists(abs_path) else "null"

    prox_sim_js  = js_path(os.path.join(layers_dir, "proximidade_simulada.png"),    "layers/proximidade_simulada.png")
    prox_act_js  = js_path(os.path.join(layers_dir, "proximidade_300m.png"),         "layers/proximidade_300m.png")
    sfca_sim_js  = js_path(os.path.join(layers_dir, "acessibilidade_2sfca_sim.png"), "layers/acessibilidade_2sfca_sim.png")
    sfca_act_js  = js_path(os.path.join(layers_dir, "acessibilidade_2sfca.png"),     "layers/acessibilidade_2sfca.png")
    lowpop_js    = js_path(os.path.join(layers_dir, "baixa_densidade.png"),           "layers/baixa_densidade.png")
    muni_js      = js_path(os.path.join(parent_layers_dir, "municipios_colored.png"), "../layers/municipios_colored.png")

    basemaps = [
        ("CartoDB Positron", "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"),
        ("CartoDB Dark", "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"),
        ("OpenStreetMap", "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"),
        ("Satélite", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"),
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
<link rel="icon" type="image/png" href="../favicon.png">
<link rel="icon" type="image/x-icon" href="../favicon.ico">
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
  .ab-group {{ display:flex; gap:4px; margin:2px 0 6px; }}
  .ab-btn {{
    flex:1; padding:5px 4px; border:1px solid #ccc; border-radius:5px;
    background:#f5f5f5; color:#555; font-size:11px; cursor:pointer;
    font-family:'Segoe UI',Arial,sans-serif; line-height:1.3; text-align:center;
  }}
  .ab-btn:hover {{ background:#e0e0e0; }}
  .ab-btn.active {{ background:#00897B; color:#fff; border-color:#00897B; font-weight:bold; }}
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
    #panel .ab-btn {{ font-size:10px; padding:4px 2px; }}
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
{get_nav('acessibilidade/conversao_verde.html', depth=1)}
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
        <span style="color:#666;">Verde em PDM / fechado ao p&uacute;blico</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#1565C0;display:inline-block;"></span>
        <span style="color:#666;">Verde privado</span>
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
    <div class="section" style="margin-top:6px;">Acessibilidade 500m (m&sup2;/hab)</div>
    <div style="display:flex;flex-direction:column;gap:2px;font-size:10px;">
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#2E7D32;display:inline-block;"></span>
        <span style="color:#666;">Adequado (&ge;9 m&sup2;/hab)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#E8A838;display:inline-block;"></span>
        <span style="color:#666;">Insuficiente (3&ndash;9 m&sup2;/hab)</span>
      </div>
      <div style="display:flex;align-items:center;gap:4px;">
        <span style="width:14px;height:12px;border-radius:2px;background:#B71C1C;display:inline-block;"></span>
        <span style="color:#666;">D&eacute;fice cr&iacute;tico (&lt;3 m&sup2;/hab)</span>
      </div>
    </div>
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

var baseTile = L.tileLayer('{basemaps[0][1]}', {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);

document.getElementById('basemap-select').addEventListener('change', function() {{
  map.removeLayer(baseTile);
  baseTile = L.tileLayer(this.value, {{maxZoom:19, attribution:'&copy; OpenStreetMap'}}).addTo(map);
}});

var bounds = {bounds};
var PROX_SIM_SRC  = {prox_sim_js};
var PROX_ACT_SRC  = {prox_act_js};
var SFCA_SIM_SRC  = {sfca_sim_js};
var SFCA_ACT_SRC  = {sfca_act_js};
var LOWPOP_SRC    = {lowpop_js};
var MUNI_SRC      = {muni_js};

function init() {{
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

  // --- Candidatos GeoJSON (polígonos + popups) ---
  var candGeoLayer = null;
  if (candidatosData && candidatosData.features.length > 0) {{
    var tipoColors = {{
      'Estrategia de expansao (CMP)': '#00897B',
      'Verde em PDM / fechado ao publico': '#8D6E63',
      'Verde privado': '#1565C0'
    }};
    candGeoLayer = L.geoJson(candidatosData, {{
      pane: 'candGeoPane',
      filter: function(f) {{ return f.properties.tipo !== 'Parques e Jardins já existentes' && f.properties.tipo !== 'Parques e Jardins ja existentes'; }},
      style: function(f) {{
        var color = tipoColors[f.properties.tipo] || '#888';
        return {{
          color: color, weight: 2, opacity: 1,
          fillColor: color, fillOpacity: 0.45
        }};
      }},
      onEachFeature: function(f, layer) {{
        var p = f.properties;
        var html = '<b style="font-size:13px;">#' + p.rank + '</b>';
        if (p.nome) html += ' &mdash; ' + p.nome;
        html += '<br><span style="color:#666;">' + p.tipo + '</span>';
        html += '<br><span style="color:#666;">&Aacute;rea: ' + p.area_ha + ' ha</span>';
        if (p.pop_delta != null) {{
          html += '<br><span style="color:#2E7D32;">+' + p.pop_delta.toLocaleString() + ' hab cobertos</span>';
          html += '<br><span style="color:#444;">Cobertura: ' + p.pct_antes + '% &rarr; ' + p.pct_depois + '%</span>';
        }}
        layer.bindPopup(html);
      }}
    }});
    candGeoLayer.addTo(map);
  }}

  // --- Overlays ---
  var proxSimOverlay = PROX_SIM_SRC ? L.imageOverlay(PROX_SIM_SRC, bounds, {{opacity: 0.7, pane: 'proxPane'}}) : null;
  var proxActOverlay = PROX_ACT_SRC ? L.imageOverlay(PROX_ACT_SRC, bounds, {{opacity: 0.7, pane: 'proxPane'}}) : null;
  var sfcaSimOverlay = SFCA_SIM_SRC ? L.imageOverlay(SFCA_SIM_SRC, bounds, {{opacity: 0.7, pane: 'proxPane'}}) : null;
  var sfcaActOverlay = SFCA_ACT_SRC ? L.imageOverlay(SFCA_ACT_SRC, bounds, {{opacity: 0.7, pane: 'proxPane'}}) : null;
  var lowPopOverlay  = LOWPOP_SRC   ? L.imageOverlay(LOWPOP_SRC, bounds, {{pane: 'lowPopPane'}}) : null;

  // Default: proximidade simulada
  if (proxSimOverlay) proxSimOverlay.addTo(map);
  if (lowPopOverlay) lowPopOverlay.addTo(map);

  function activateOverlay(overlay, withLowPop) {{
    if (proxSimOverlay) map.removeLayer(proxSimOverlay);
    if (proxActOverlay) map.removeLayer(proxActOverlay);
    if (sfcaSimOverlay) map.removeLayer(sfcaSimOverlay);
    if (sfcaActOverlay) map.removeLayer(sfcaActOverlay);
    if (lowPopOverlay)  map.removeLayer(lowPopOverlay);
    if (overlay) {{
      overlay.addTo(map);
      if (withLowPop && lowPopOverlay) lowPopOverlay.addTo(map);
    }}
  }}

  // --- Grupos A/B: Proximidade ---
  var proxLabel = document.createElement('div'); proxLabel.className = 'section'; proxLabel.style.marginTop = '4px';
  proxLabel.textContent = 'Proximidade 300m';
  div.appendChild(proxLabel);

  var proxGroup = document.createElement('div'); proxGroup.className = 'ab-group';

  var proxActBtn = document.createElement('button'); proxActBtn.className = 'ab-btn';
  proxActBtn.textContent = 'Actual {pct_actual:.0f}%';

  var proxSimBtn = document.createElement('button'); proxSimBtn.className = 'ab-btn active';
  proxSimBtn.textContent = 'Simulado {pct:.0f}%';

  proxGroup.appendChild(proxActBtn); proxGroup.appendChild(proxSimBtn);
  div.appendChild(proxGroup);

  // --- Grupos A/B: 2SFCA ---
  var sfcaLabel = document.createElement('div'); sfcaLabel.className = 'section'; sfcaLabel.style.marginTop = '4px';
  sfcaLabel.textContent = 'Acessibilidade 500m';
  div.appendChild(sfcaLabel);

  var sfcaGroup = document.createElement('div'); sfcaGroup.className = 'ab-group';

  var sfcaActBtn = document.createElement('button'); sfcaActBtn.className = 'ab-btn';
  sfcaActBtn.textContent = 'Actual {sfca_actual_label}';

  var sfcaSimBtn = document.createElement('button'); sfcaSimBtn.className = 'ab-btn';
  sfcaSimBtn.textContent = 'Simulado {sfca_sim_label}';

  sfcaGroup.appendChild(sfcaActBtn); sfcaGroup.appendChild(sfcaSimBtn);
  div.appendChild(sfcaGroup);

  function clearActive() {{
    proxActBtn.classList.remove('active');
    proxSimBtn.classList.remove('active');
    sfcaActBtn.classList.remove('active');
    sfcaSimBtn.classList.remove('active');
  }}

  proxActBtn.addEventListener('click', function() {{
    if (this.classList.contains('active')) {{
      clearActive(); activateOverlay(null, false);
    }} else {{
      clearActive(); this.classList.add('active');
      activateOverlay(proxActOverlay, true);
    }}
  }});

  proxSimBtn.addEventListener('click', function() {{
    if (this.classList.contains('active')) {{
      clearActive(); activateOverlay(null, false);
    }} else {{
      clearActive(); this.classList.add('active');
      activateOverlay(proxSimOverlay, true);
    }}
  }});

  sfcaActBtn.addEventListener('click', function() {{
    if (this.classList.contains('active')) {{
      clearActive(); activateOverlay(null, false);
    }} else {{
      clearActive(); this.classList.add('active');
      activateOverlay(sfcaActOverlay, true);
    }}
  }});

  sfcaSimBtn.addEventListener('click', function() {{
    if (this.classList.contains('active')) {{
      clearActive(); activateOverlay(null, false);
    }} else {{
      clearActive(); this.classList.add('active');
      activateOverlay(sfcaSimOverlay, true);
    }}
  }});

  // --- Contexto: municipios ---
  var ctxLayers = [
    {{ id: "municipios", label: "Limites municipais", color: "#444444", src: MUNI_SRC, show: true }},
  ];
  var ctxOverlays = [];

  for (var i = 0; i < ctxLayers.length; i++) {{
    var L_ = ctxLayers[i];
    if (!L_.src) {{ ctxOverlays.push(null); continue; }}
    var ov = L.imageOverlay(L_.src, bounds);
    if (L_.show) ov.addTo(map);
    ctxOverlays.push(ov);

    var row = document.createElement('div'); row.className = 'row';
    var cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = L_.show; cb.dataset.idx = i;
    cb.addEventListener('change', function() {{
      var idx = +this.dataset.idx;
      var ov = ctxOverlays[idx];
      if (!ov) return;
      if (this.checked) ov.addTo(map); else map.removeLayer(ov);
    }});
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.backgroundColor = L_.color;
    var lb = document.createElement('label'); lb.textContent = L_.label; lb.style.fontSize = '12px';
    row.appendChild(cb); row.appendChild(sw); row.appendChild(lb);
    ctxDiv.appendChild(row);
  }}

  // --- Parques GeoJSON ---
  var parquesGeoLayer = null;
  var pRow = document.createElement('div'); pRow.className = 'row';
  var pCb = document.createElement('input'); pCb.type = 'checkbox'; pCb.checked = false;
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
  ctxDiv.appendChild(pRow);

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

  if (parquesData) initParques();
}}

init();
</script>
<div id="credit" style="position:fixed;bottom:6px;right:10px;z-index:1000;font:10px 'Segoe UI',Arial,sans-serif;color:#888;background:rgba(255,255,255,0.85);padding:2px 8px;border-radius:4px;">
  <a href="https://www.linkedin.com/in/nquental/" target="_blank" style="color:#555;text-decoration:none;">Nuno Quental</a>
</div>
<script>if(window.innerWidth<=768){{var p=document.getElementById('panel'),b=document.getElementById('panel-toggle');p.classList.add('collapsed');b.textContent='▲ Abrir legenda';}}</script>
</body>
</html>'''

    output_path = os.path.join(script_dir, "conversao_verde.html")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"\nMapa gerado: {output_path}")
    print(f"  Tamanho: {os.path.getsize(output_path) // 1024} KB")
    print("\nConcluido.")
