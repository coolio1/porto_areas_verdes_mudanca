---
layout: default
title: "Campanha «50 Espaços Verdes»: mapa e lista dos espaços"
description: "Os 111 espaços verdes da Área Metropolitana do Porto identificados pela Campo Aberto, 50 deles seleccionados: mapa, lista e filtros por concelho."
wide: true
---
<link rel="stylesheet" href="{{ site.baseurl }}/assets/css/50espacos.css?v={{ site.time | date: '%s' }}">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<div class="e50">
  <div class="lista-pagina">
    {% include topo_campanha.html %}
    <h1 class="so-leitor">Campanha «50 Espaços Verdes»: mapa e lista dos espaços</h1>
    {%- assign n_sel = site.espacos | where_exp: "e", "e.seleccionado == true" | size -%}
    {%- assign n_conc = site.espacos | map: "concelho" | uniq | size -%}
    <dl class="faixa">
      <div><dt>espaços</dt><dd>{{ site.espacos.size }}</dd></div>
      <div><dt>seleccionados</dt><dd>{{ n_sel }}</dd></div>
      <div><dt>concelhos</dt><dd>{{ n_conc }}</dd></div>
    </dl>
    <form class="filtros" aria-label="Filtros">
      <label class="filtro-select">Concelho
        <select id="f-concelho"><option value="">Todos</option>
        {%- assign concelhos = site.espacos | map: "concelho" | uniq | sort -%}
        {%- for c in concelhos %}<option value="{{ c }}">{{ c }}</option>{% endfor -%}
        </select>
      </label>
      <label class="filtro-pilula"><input type="checkbox" id="f-50"><span>Só os 50</span></label>
      <p class="contagem" id="contagem" aria-live="polite"></p>
    </form>
    <div class="lista-mapa">
      <ul class="espacos-lista" id="espacos-lista">
        {%- assign ordenados = site.espacos | sort: "titulo" -%}
        {%- for e in ordenados %}
        {%- assign thumb = "" -%}
        {%- for f in e.fotos -%}{%- unless f.src contains "/mapa" or f.src contains "delimitacao" -%}{%- if thumb == "" -%}{%- assign thumb = f.src -%}{%- endif -%}{%- endunless -%}{%- endfor %}
        <li data-slug="{{ e.slug }}" data-concelho="{{ e.concelho }}" data-50="{{ e.seleccionado | default: false }}">
          <a href="{{ e.url | relative_url }}">
            {%- if thumb != "" %}<img src="{{ thumb | relative_url }}" alt="" loading="lazy">{% else %}<span class="sem-foto" aria-hidden="true"></span>{% endif %}
            <span class="info">
              <span class="nome">{{ e.titulo }}</span>
              <span class="local">{% if e.freguesia %}{{ e.freguesia }}, {% endif %}{{ e.concelho }}</span>
              {%- if e.seleccionado %}<span class="de-50">Entre os 50</span>{% endif %}
            </span>
          </a>
        </li>
        {%- endfor %}
      </ul>
      <p class="vazio" id="vazio" hidden>Nenhum espaço com estes filtros.</p>
      <div class="mapa-coluna">
        <div id="mapa-espacos" class="moldura" role="img" aria-label="Mapa dos espaços"><span>Mapa</span></div>
        <p class="nota-mapa">Localizações aproximadas (2 casas decimais, cerca de 1 km).</p>
      </div>
    </div>
    {% include rodape_campanha.html %}
  </div>
</div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
(function () {
  var pontos = {{ site.data.espacos_mapa | jsonify }};
  var base = {{ site.baseurl | jsonify }};
  var el = document.getElementById('mapa-espacos');
  el.textContent = ''; el.classList.remove('moldura');
  var mapa = L.map(el, {scrollWheelZoom: false});
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {attribution: '© OpenStreetMap'}).addTo(mapa);
  var normal = function (p) { return {radius: 8, weight: 2, color: '#23282B', fillOpacity: 0.9, fillColor: p.seleccionado ? '#2E7D32' : '#F6F7F4'}; };
  var marcas = {}, grupo = [];
  pontos.forEach(function (p) {
    var m = L.circleMarker([p.lat, p.lon], normal(p)).addTo(mapa);
    m.bindTooltip(p.titulo);
    m.on('click', function () { location.href = base + '/50espacos/espacos/' + p.concelho + '/' + p.slug + '/'; });
    marcas[p.slug] = {m: m, p: p};
    grupo.push([p.lat, p.lon]);
  });
  if (grupo.length) mapa.fitBounds(grupo, {padding: [30, 30], animate: false}); else mapa.setView([41.16, -8.62], 12);

  var legenda = L.control({position: 'bottomleft'});
  legenda.onAdd = function () {
    var d = L.DomUtil.create('div', 'legenda-mapa');
    d.innerHTML = '<span><i class="ponto sel"></i> Entre os 50</span><span><i class="ponto"></i> Outros espaços</span>';
    return d;
  };
  legenda.addTo(mapa);

  var itens = document.querySelectorAll('#espacos-lista li');
  function realcar(slug, sim) {
    var k = marcas[slug]; if (!k) return;
    k.m.setStyle(sim ? {radius: 12, weight: 3, color: '#E8C21A'} : normal(k.p));
    if (sim) k.m.bringToFront();
  }
  itens.forEach(function (li) {
    li.addEventListener('mouseenter', function () { realcar(li.dataset.slug, true); });
    li.addEventListener('mouseleave', function () { realcar(li.dataset.slug, false); });
    li.querySelector('a').addEventListener('focus', function () { realcar(li.dataset.slug, true); });
    li.querySelector('a').addEventListener('blur', function () { realcar(li.dataset.slug, false); });
  });
  Object.keys(marcas).forEach(function (slug) {
    var li = document.querySelector('#espacos-lista li[data-slug="' + slug + '"]');
    marcas[slug].m.on('mouseover', function () { if (li) li.classList.add('activo'); });
    marcas[slug].m.on('mouseout', function () { if (li) li.classList.remove('activo'); });
  });

  function filtrar() {
    var c = document.getElementById('f-concelho').value, so50 = document.getElementById('f-50').checked, n = 0, visiveis = [];
    itens.forEach(function (li) {
      var ok = (!c || li.dataset.concelho === c) && (!so50 || li.dataset['50'] === 'true');
      li.hidden = !ok;
      var k = marcas[li.dataset.slug];
      if (ok) n++;
      if (k) { if (ok) { k.m.addTo(mapa); visiveis.push([k.p.lat, k.p.lon]); } else mapa.removeLayer(k.m); }
    });
    document.getElementById('contagem').textContent = n + (n === 1 ? ' espaço' : ' espaços');
    document.getElementById('vazio').hidden = n > 0;
    if (visiveis.length) mapa.fitBounds(visiveis, {padding: [30, 30], maxZoom: 15, animate: false});
  }
  document.getElementById('f-concelho').addEventListener('change', filtrar);
  document.getElementById('f-50').addEventListener('change', filtrar);
  filtrar();
})();
</script>
