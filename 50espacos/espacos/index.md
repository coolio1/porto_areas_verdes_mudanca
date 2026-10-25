---
layout: default
title: Os espaços da campanha
description: Mapa e lista dos espaços verdes da campanha 50 espaços verdes da Campo Aberto.
wide: true
---
<link rel="stylesheet" href="{{ site.baseurl }}/assets/css/50espacos.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<div class="e50">
  <div class="coluna">
    <p class="migalhas"><a href="{{ '/50espacos/' | relative_url }}">50 Espaços</a> / Espaços</p>
    <h1>Os espaços da campanha</h1>
  </div>
  <div id="mapa-espacos" class="moldura" style="min-height:26rem;margin:1rem 0 0.4rem" role="img" aria-label="Mapa dos espaços"><span>Mapa</span></div>
  <p class="nota-mapa coluna">Localizações aproximadas (WGS84, 2 casas decimais ≈ 1 km); fonte: ficha da campanha ou Webnode, conforme a ficha de cada espaço.</p>
  <form class="filtros coluna" aria-label="Filtros">
    <label>Concelho
      <select id="f-concelho"><option value="">Todos</option>
      {%- assign concelhos = site.espacos | map: "concelho" | uniq | sort -%}
      {%- for c in concelhos %}<option value="{{ c }}">{{ c }}</option>{% endfor -%}
      </select>
    </label>
    <label><input type="checkbox" id="f-50"> Só os 50</label>
  </form>
  <table class="lista coluna">
    <thead><tr><th>Espaço</th><th>Concelho</th><th>Freguesia</th><th>Selecção</th><th>Estado actual</th></tr></thead>
    <tbody>
    {%- assign ordenados = site.espacos | sort: "titulo" -%}
    {%- for e in ordenados %}
      <tr data-slug="{{ e.slug }}" data-concelho="{{ e.concelho }}" data-50="{{ e.seleccionado | default: false }}">
        <td><a href="{{ e.url | relative_url }}">{{ e.titulo }}</a></td>
        <td>{{ e.concelho }}</td><td>{{ e.freguesia }}</td>
        <td>{% if e.seleccionado %}{% if e.selecao == "posterior" %}Entre os 50 (depois de Abril de 2009){% else %}Entre os 50 (Abril de 2009){% endif %}{% else %}Entre os 111{% endif %}</td>
        <td>{{ e.estado_actual | default: "por verificar" }}</td>
      </tr>
    {%- endfor %}
    </tbody>
  </table>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function () {
  var pontos = {{ site.data.espacos_mapa | jsonify }};
  var base = {{ site.baseurl | jsonify }};
  var el = document.getElementById('mapa-espacos');
  el.textContent = ''; el.classList.remove('moldura');
  var mapa = L.map(el).setView([41.16, -8.62], 12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '© OpenStreetMap'}).addTo(mapa);
  var marcas = {};
  pontos.forEach(function (p) {
    var m = L.circleMarker([p.lat, p.lon], {radius: 8, weight: 2, color: '#23282B', fillOpacity: 0.9,
      fillColor: p.seleccionado ? '#2E7D32' : '#F6F7F4'}).addTo(mapa);
    m.bindTooltip(p.titulo);
    m.on('click', function () { location.href = base + '/50espacos/espacos/' + p.concelho + '/' + p.slug + '/'; });
    marcas[p.slug] = {m: m, p: p};
  });
  var linhas = document.querySelectorAll('table.lista tbody tr');
  function filtrar() {
    var c = document.getElementById('f-concelho').value, so50 = document.getElementById('f-50').checked;
    linhas.forEach(function (tr) {
      var ok = (!c || tr.dataset.concelho === c) && (!so50 || tr.dataset['50'] === 'true');
      tr.hidden = !ok;
      var k = marcas[tr.dataset.slug];
      if (k) { if (ok) k.m.addTo(mapa); else mapa.removeLayer(k.m); }
    });
  }
  document.getElementById('f-concelho').addEventListener('change', filtrar);
  document.getElementById('f-50').addEventListener('change', filtrar);
})();
</script>
