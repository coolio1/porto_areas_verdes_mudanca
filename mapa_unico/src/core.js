/* Núcleo do mapa único do Porto Verde. Tudo vive em window.MU (sem globais soltas):
   cada tema regista-se com MU.registarTema() e só é montado quando é aberto.
   Gramática «Carta» (maquete V2b): separadores fixos dos temas com cor-guia, números-chave, camadas com amostra
   que é o interruptor e barra de hectares, fundo do mapa sobre o mapa, ficha do parque, moldura de carta
   (quadrícula, esquadria, área fora do estudo tracejada) e fundo «Carta» sem mosaicos. */
(function () {
  var BOUNDS = [[41.13, -8.7], [41.19, -8.54]];
  var B = { S: 41.13, N: 41.19, W: -8.7, E: -8.54 };
  var MU = window.MU = { TEMAS: {}, ORDEM: [], DADOS: {}, BOUNDS: BOUNDS, tema: null };
  var TINTA = '#10212C', PARQUE = '#0B5232', PARQUE_ORLA = '#06301D';

  /* ---------- utilitários partilhados ---------- */
  MU.hexToRgb = function (h) {
    h = h.replace('#', '');
    return [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)];
  };
  MU.n = function (x, d) { return Number(x).toLocaleString('pt-PT', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  MU.ha = function (x) { return MU.n(x, x < 100 ? 1 : 0) + ' ha'; };

  MU.extractMask = function (src) {
    return new Promise(function (resolve) {
      var i = new Image();
      i.onload = function () {
        var c = document.createElement('canvas');
        c.width = i.width; c.height = i.height;
        var x = c.getContext('2d');
        x.drawImage(i, 0, 0);
        var d = x.getImageData(0, 0, c.width, c.height);
        var a = new Uint8Array(d.data.length / 4);
        for (var j = 0; j < a.length; j++) a[j] = d.data[j * 4 + 3];
        resolve({ w: c.width, h: c.height, alpha: a });
      };
      i.src = src;
    });
  };

  /* op (0-1) multiplica o alpha; por omissão 1 = alpha original */
  MU.renderColored = function (m, hex, op) {
    op = (op === undefined) ? 1 : op;
    var rgb = MU.hexToRgb(hex);
    var c = document.createElement('canvas');
    c.width = m.w; c.height = m.h;
    var x = c.getContext('2d');
    var d = x.createImageData(m.w, m.h);
    for (var i = 0; i < m.alpha.length; i++) {
      d.data[i * 4] = rgb[0]; d.data[i * 4 + 1] = rgb[1];
      d.data[i * 4 + 2] = rgb[2]; d.data[i * 4 + 3] = m.alpha[i] * op;
    }
    x.putImageData(d, 0, 0);
    return c.toDataURL();
  };

  /* Camada de máscara recolorível: {overlay, setColor(hex), cor}. bounds por omissão = BOUNDS. */
  MU.camadaMascara = async function (o) {
    var m = await MU.extractMask(o.src);
    var cam = { mask: m, cor: o.color, overlay: null };
    var opc = {}; if (o.pane) opc.pane = o.pane; if (o.op != null) opc.opacity = o.op;
    cam.overlay = L.imageOverlay(MU.renderColored(m, o.color), o.bounds || BOUNDS, opc);
    cam.setColor = function (hex) { cam.cor = hex; cam.overlay.setUrl(MU.renderColored(m, hex)); };
    return cam;
  };

  /* ---------- peças do painel ---------- */
  MU.cab2 = function (esq, dir) { return '<div class="cab2"><span>' + esq + '</span><span>' + (dir || '') + '</span></div>'; };
  /* números-chave: [{v, u, r}] — o primeiro é o grande */
  MU.htmlNums = function (N) {
    return '<div class="num mor"><b>' + N[0].v + '<small>' + N[0].u + '</small></b><p>' + N[0].r + '</p></div>' +
      N.slice(1).map(function (n) { return '<div class="num"><b>' + n.v + '<small>' + n.u + '</small></b><p>' + n.r + '</p></div>'; }).join('');
  };
  /* escala comum das barras de hectares de um tema: 400, 1000 ou 3000 ha */
  MU.escala = function (has) {
    var max = Math.max.apply(null, has.concat([1]));
    return max > 1500 ? 3000 : max > 600 ? 1000 : 400;
  };

  /* Linha de camada: amostra = interruptor (--sw), rótulo, hectares + barra, legenda de categorias, opacidade.
     o: {label, checked, color, contorno, ha, esc, leg:[[cor, texto, tracejado?]], nota, sub, id,
         onToggle(on), opacidade:{v, min, max, step, id, onInput(v)}} */
  var nLinha = 0;
  MU.linha = function (container, o) {
    var id = o.id || ('mu-l' + (++nLinha));
    var row = document.createElement('div');
    row.className = 'cam' + (o.checked ? '' : ' off') + (o.sub ? ' sub' : '');
    if (o.color) row.style.setProperty('--sw', o.color);
    var h = '<input type="checkbox" id="' + id + '"' + (o.checked ? ' checked' : '') + (o.contorno ? ' class="contorno"' : '') + '>' +
      '<label for="' + id + '">' + o.label + '</label><span class="ha">' + (o.ha ? MU.ha(o.ha) : '') + '</span>' +
      (o.opacidade ? '<button type="button" class="opb" aria-expanded="false" aria-label="Opacidade: ' + o.label.replace(/<[^>]+>/g, '') + '" title="Opacidade">' +
        '<svg viewBox="0 0 14 14" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M7 1.5a5.5 5.5 0 0 1 0 11z" fill="currentColor"/></svg></button>' : '');
    if (o.ha && o.esc && o.ha <= o.esc) h += '<div class="med" aria-hidden="true"><i style="width:' + Math.min(100, o.ha / o.esc * 100).toFixed(2) + '%"></i></div>';
    if (o.leg) {
      h += '<div class="catleg">' + o.leg.map(function (l) {
        return '<span><i' + (l[2] ? ' class="trac"' : '') + ' style="background:' + l[0] + '"></i>' + l[1] + '</span>';
      }).join('') + (o.nota ? '<span><i></i>' + o.nota + '</span>' : '') + '</div>';
    }
    if (o.opacidade) {
      var p = o.opacidade;
      h += '<div class="op"><input type="range"' + (p.id ? ' id="' + p.id + '"' : '') + ' min="' + (p.min || 0.1) + '" max="' + (p.max || 1) +
        '" step="' + (p.step || 0.05) + '" value="' + p.v + '" aria-label="Opacidade: ' + o.label.replace(/<[^>]+>/g, '') + '"></div>';
    }
    row.innerHTML = h;
    container.appendChild(row);
    var cb = row.querySelector('input[type=checkbox]');
    cb.addEventListener('change', function () {
      row.classList.toggle('off', !cb.checked);
      if (o.onToggle) o.onToggle(cb.checked);
    });
    var opb = row.querySelector('.opb');
    if (opb) opb.addEventListener('click', function () { var a = row.classList.toggle('opa'); opb.setAttribute('aria-expanded', a); });
    var op = row.querySelector('.op input');
    if (op) op.addEventListener('input', function () { o.opacidade.onInput(+op.value); });
    return { row: row, cb: cb, op: op };
  };

  /* Cria camadas de máscara + linhas do painel para defs [{id,label,color,show,op,ha}] (dados em
     MU.DADOS[tema.dados][id]) e guarda-as em tema._camadas, para activar/desactivar em bloco. */
  /* Pane com nível fixo: a ordem das camadas no mapa não depende da ordem em que se ligam.
     Regra: topo da lista do painel = topo do mapa (z maior); cada def indica o seu z (< 540, o dos parques). */
  MU.pane = function (nome, z) {
    if (!MU.map.getPane(nome)) MU.map.createPane(nome);
    MU.map.getPane(nome).style.zIndex = z;
    return nome;
  };
  MU.addCamadas = async function (tema, box, defs, esc) {
    tema._camadas = tema._camadas || [];
    for (var i = 0; i < defs.length; i++) {
      var c = defs[i];
      var cam = await MU.camadaMascara({ src: MU.DADOS[tema.dados][c.id], color: c.color, op: c.op, pane: c.z ? MU.pane('mu-' + tema.id + '-' + c.id, c.z) : undefined });
      var l = { cam: cam, linha: null };
      l.linha = MU.linha(box, {
        label: c.label, checked: c.show !== false, color: c.color, ha: c.ha, esc: esc,
        onToggle: (function (l) {
          return function (on) {
            if (MU.tema !== tema.id) return;
            on ? l.cam.overlay.addTo(MU.map) : MU.map.removeLayer(l.cam.overlay);
          };
        })(l),
        opacidade: { v: c.op == null ? 1 : c.op, onInput: (function (l) { return function (v) { l.cam.overlay.setOpacity(v); }; })(l) }
      });
      tema._camadas.push(l);
    }
  };
  MU.activarCamadas = function (tema) {
    (tema._camadas || []).forEach(function (l) { if (l.linha.cb.checked) l.cam.overlay.addTo(MU.map); });
  };
  MU.desactivarCamadas = function (tema) {
    (tema._camadas || []).forEach(function (l) { MU.map.removeLayer(l.cam.overlay); });
  };

  MU.carregarDados = function (nome) {
    MU._dadosP = MU._dadosP || {};
    if (!MU._dadosP[nome]) {
      MU._dadosP[nome] = new Promise(function (resolve, reject) {
        var s = document.createElement('script');
        s.src = 'dados/' + nome + '.js';
        s.onload = function () { resolve(MU.DADOS[nome]); };
        s.onerror = function () { reject(new Error('Falha ao carregar dados/' + nome + '.js')); };
        document.head.appendChild(s);
      });
    }
    return MU._dadosP[nome];
  };

  /* ---------- ficha (parque ou candidato), no canto do mapa ---------- */
  MU.ficha = function (f) {
    var box = document.getElementById('ficha');
    if (MU._sel) { MU._sel.grupo.resetStyle(MU._sel.layer); MU._sel = null; }
    if (!f) { box.classList.remove('on'); box.innerHTML = ''; return; }
    if (f.layer && f.grupo) { MU._sel = { layer: f.layer, grupo: f.grupo }; f.layer.setStyle({ color: TINTA, weight: 2.6 }); }
    box.style.setProperty('--fc', f.cor || PARQUE);
    box.innerHTML = '<button type="button" class="x" aria-label="Fechar a ficha">×</button><h3>' + f.titulo + '</h3><p class="sub">' + f.sub + '</p><dl>' +
      f.linhas.map(function (l) { return '<dt>' + l[0] + '</dt><dd>' + l[1] + '</dd>'; }).join('') + '</dl>' +
      (f.rel != null ? '<div class="cmp">Área face ao Parque da Cidade (' + MU.n(MU._maiorParque, 2) + ' ha)<div class="med"><i style="width:' +
        Math.max(1, f.rel * 100).toFixed(1) + '%"></i></div></div>' : '');
    box.classList.add('on');
    box.querySelector('.x').onclick = function () { MU.ficha(null); };
  };

  /* ---------- parques e jardins: camada comum (cheia ou só contorno), ficha, «Ir para um parque» ---------- */
  var TIPO_P = { jardim: 'Jardim', parque: 'Parque', 'praça': 'Praça', quinta: 'Quinta' };
  MU._parques = {};
  MU.fichaParque = function (i, layer, grupo) {
    var P = MU.PARQUES[i], g = P.f.properties, S = MU.DADOS.contexto.stats, c = P.centro;
    MU.ficha({
      titulo: g.nome, cor: PARQUE, layer: layer, grupo: grupo,
      sub: (TIPO_P[g.tipo] || g.tipo || '') + ' · polígono ' + (g.fonte === 'osm' ? 'OpenStreetMap' : 'CMP'),
      linhas: [['Área', MU.n(g.area_calc_ha || 0, 2) + ' ha'],
               ['Dos parques do concelho', MU.n((g.area_calc_ha || 0) / S.parques_ha * 100, 1) + ' %'],
               ['Centro', MU.n(c.lat, 4) + ' N, ' + MU.n(Math.abs(c.lng), 4) + ' O']],
      rel: (g.area_calc_ha || 0) / MU._maiorParque
    });
  };
  MU.parques = function (estilo) {   // 'cheio' | 'contorno'
    if (MU._parques[estilo]) return MU._parques[estilo];
    var cont = estilo === 'contorno';
    var g = L.geoJson(MU.DADOS.contexto.parques, {
      pane: 'parquesPane',
      style: function () {
        return cont ? { color: PARQUE, weight: 1.6, opacity: 1, fillColor: PARQUE, fillOpacity: 0 }
                    : { color: PARQUE_ORLA, weight: 0.9, opacity: 1, fillColor: PARQUE, fillOpacity: 1 };
      },
      onEachFeature: function (f, layer) {
        layer.on('click', function (e) {
          L.DomEvent.stopPropagation(e);
          MU.fichaParque(MU.DADOS.contexto.parques.features.indexOf(f), layer, g);
        });
      }
    });
    g.on('add remove', function () { MU.desenharCarta(); });
    return (MU._parques[estilo] = g);
  };
  MU.parquesVisiveis = function () {
    return Object.keys(MU._parques).some(function (k) { return MU.map.hasLayer(MU._parques[k]); });
  };
  /* linha «Parques e jardins» de um tema; tema.linhaParques serve ao «Ir para um parque» */
  MU.linhaParques = function (tema, box, o) {
    var camada = MU.parques(o.contorno ? 'contorno' : 'cheio');
    tema._parquesCamada = camada;
    tema.linhaParques = MU.linha(box, {
      label: o.label || 'Parques e jardins', checked: o.on, color: PARQUE, contorno: o.contorno,
      ha: o.ha === false ? null : MU.DADOS.contexto.stats.parques_ha, esc: o.esc,
      onToggle: function (on) {
        if (MU.tema !== tema.id) return;
        on ? camada.addTo(MU.map) : MU.map.removeLayer(camada);
      },
      opacidade: { v: 1, onInput: function (v) { camada.setStyle(o.contorno ? { opacity: v } : { fillOpacity: v }); } }
    });
    return tema.linhaParques;
  };
  MU.activarParques = function (tema) { if (tema.linhaParques && tema.linhaParques.cb.checked) tema._parquesCamada.addTo(MU.map); };
  MU.desactivarParques = function (tema) { if (tema._parquesCamada) MU.map.removeLayer(tema._parquesCamada); };

  /* ---------- fundos de mapa (lista única; temas podem acrescentar o seu) ---------- */
  var ATTR = '&copy; OpenStreetMap';
  MU.FUNDOS = [
    { id: 'carta', nome: 'Carta (sem mosaicos)', criar: function () { return MU.ctx.carta(); } },
    { id: 'positron', nome: 'CartoDB Positron', url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png' },
    { id: 'dark', nome: 'CartoDB Dark', url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png' },
    { id: 'osm', nome: 'OpenStreetMap', url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png' },
    { id: 'satelite', nome: 'Satélite', url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}' }
  ];
  MU.fundoActual = null;
  MU.setFundo = function (id) {
    var f = MU.FUNDOS.filter(function (x) { return x.id === id; })[0];
    if (!f) return;
    if (MU.baseTile) MU.map.removeLayer(MU.baseTile);
    MU.baseTile = f.criar ? f.criar() : L.tileLayer(f.url, { maxZoom: 19, attribution: ATTR });
    MU.baseTile.addTo(MU.map);
    if (MU.baseTile.bringToBack) MU.baseTile.bringToBack();
    MU.fundoActual = id;
    MU.map.getContainer().classList.toggle('fundo-carta', id === 'carta');
    document.getElementById('fundo-select').value = id;
    MU.desenharCarta();
  };

  /* ---------- Contexto comum (limites, densidade) e peças do fundo «Carta» ---------- */
  MU.ctx = { itens: {}, estado: {} };   // estado[temaId] = {limites:{on}, densidade:{on}}
  var CTX_DEF = { limites: { on: true }, densidade: { on: false } };

  async function montarContexto() {
    var d = await MU.carregarDados('contexto');
    var map = MU.map;
    var lim = await MU.camadaMascara({ src: d.municipios, color: TINTA, pane: 'limitesPane', op: 0.9 });
    var dens = L.imageOverlay(d.ghspop, BOUNDS, { opacity: 0.7, pane: 'bgPane' });
    MU.ctx.itens = { limites: lim, densidade: dens };
    /* fundo «Carta»: placa de papel, água (Landsat, layers_historico/rio.png) e véu sobre os concelhos vizinhos */
    var agua = await MU.extractMask(d.agua), fora = await MU.extractMask(d.fora);
    var placa = L.rectangle(BOUNDS, { pane: 'placaPane', stroke: false, fillColor: '#E6EDEB', fillOpacity: 1, interactive: false });
    var ovAgua = L.imageOverlay(MU.renderColored(agua, '#A9CADB'), BOUNDS, { pane: 'cartaPane' });
    var veu = L.imageOverlay(MU.renderColored(fora, '#E6EDEB'), BOUNDS, { pane: 'veuPane', opacity: 0.58 });
    MU.ctx.carta = function () { return L.featureGroup([placa, ovAgua, veu]); };
    var box = document.getElementById('ctx-rows');
    MU.ctx.rowLim = MU.linha(box, {
      label: 'Limites municipais', checked: true, color: TINTA,
      onToggle: function (on) { on ? lim.overlay.addTo(map) : map.removeLayer(lim.overlay); }
    });
    MU.ctx.rowDens = MU.linha(box, {
      label: 'Densidade populacional (GHS-POP)', checked: false, color: '#8b6934',
      onToggle: function (on) {
        on ? dens.addTo(map) : map.removeLayer(dens);
        document.getElementById('pop-legend').style.display = on ? 'flex' : 'none';
      }
    });
    /* parques: índice para o «Ir para um parque», rótulos e fichas */
    MU.PARQUES = d.parques.features.map(function (f) {
      var b = L.geoJson(f).getBounds();
      return { f: f, b: b, centro: b.getCenter() };
    });
    MU._maiorParque = Math.max.apply(null, d.parques.features.map(function (f) { return f.properties.area_calc_ha || 0; }));
    var sel = document.getElementById('ir');
    sel.innerHTML = '<option value="">Ir para um parque…</option>' + MU.PARQUES.map(function (p, i) { return i; })
      .sort(function (a, b) { return MU.PARQUES[a].f.properties.nome.localeCompare(MU.PARQUES[b].f.properties.nome, 'pt'); })
      .map(function (i) { return '<option value="' + i + '">' + MU.PARQUES[i].f.properties.nome + '</option>'; }).join('');
    sel.addEventListener('change', function () {
      if (sel.value === '') return;
      var i = +sel.value, t = MU.TEMAS[MU.tema], P = MU.PARQUES[i];
      if (t && t.linhaParques && !t.linhaParques.cb.checked) { t.linhaParques.cb.checked = true; t.linhaParques.cb.dispatchEvent(new Event('change')); }
      map.fitBounds(P.b, { maxZoom: 17, padding: [80, 80] });
      var g = t && t._parquesCamada, lay = null;
      if (g) g.eachLayer(function (l) { if (l.feature === P.f) lay = l; });
      MU.fichaParque(i, lay, g);
    });
  }

  function guardarCtx(id) {
    if (!MU.ctx.rowLim) return;
    MU.ctx.estado[id] = { limites: { on: MU.ctx.rowLim.cb.checked }, densidade: { on: MU.ctx.rowDens.cb.checked } };
  }
  function aplicarCtx(t) {
    if (!MU.ctx.rowLim) return;
    var e = MU.ctx.estado[t.id] || {
      limites: Object.assign({}, CTX_DEF.limites, (t.ctx || {}).limites),
      densidade: Object.assign({}, CTX_DEF.densidade, (t.ctx || {}).densidade)
    };
    MU.ctx.rowLim.cb.checked = e.limites.on;
    MU.ctx.rowLim.cb.dispatchEvent(new Event('change'));
    MU.ctx.rowDens.cb.checked = e.densidade.on;
    MU.ctx.rowDens.cb.dispatchEvent(new Event('change'));
  }

  /* ---------- moldura de carta: quadrícula, esquadria, área fora do estudo, rótulos ---------- */
  /* âncoras dos rótulos de lugares (centróides OSM/Nominatim da maquete V2b; posições fixas, sem pedidos à rede) */
  var LUGARES = [
    { n: 'Foz do Douro', lon: -8.6702, lat: 41.1514, k: 'f' }, { n: 'Lordelo do Ouro', lon: -8.6517, lat: 41.1531, k: 'f' },
    { n: 'Ramalde', lon: -8.6433, lat: 41.1700, k: 'f' }, { n: 'Boavista', lon: -8.6291, lat: 41.1579, k: 'f' },
    { n: 'Paranhos', lon: -8.6058, lat: 41.1739, k: 'f' }, { n: 'Baixa', lon: -8.6108, lat: 41.1483, k: 'f' },
    { n: 'Bonfim', lon: -8.5940, lat: 41.1511, k: 'f' }, { n: 'Campanhã', lon: -8.5750, lat: 41.1544, k: 'f' },
    { n: 'Matosinhos', lon: -8.6870, lat: 41.1860, k: 'm' }, { n: 'Maia', lon: -8.6150, lat: 41.1880, k: 'm' },
    { n: 'Gondomar', lon: -8.5520, lat: 41.1520, k: 'm' }, { n: 'Vila Nova de Gaia', lon: -8.6200, lat: 41.1330, k: 'm' },
    { n: 'Rio Douro', lon: -8.6235, lat: 41.1397, k: 'a', rot: 0.02 }, { n: 'Oceano Atlântico', lon: -8.6930, lat: 41.1610, k: 'a', rot: -Math.PI / 2 }
  ];
  var CV = null;
  function passo(pxDeg) {
    var st = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05];
    for (var i = 0; i < st.length; i++) if (st[i] * pxDeg >= 90) return st[i];
    return 0.05;
  }
  MU.desenharCarta = function () {
    var map = MU.map;
    if (!map || !CV) return;
    if (MU._rafCarta) return;
    MU._rafCarta = requestAnimationFrame(function () { MU._rafCarta = 0; desenhar(); });
  };
  function desenhar() {
    var map = MU.map, sz = map.getSize(), W = sz.x, H = sz.y, d = window.devicePixelRatio || 1;
    if (!W || !H) return;
    L.DomUtil.setPosition(CV, map.containerPointToLayerPoint([0, 0]));
    if (CV.width !== Math.round(W * d) || CV.height !== Math.round(H * d)) {
      CV.width = Math.round(W * d); CV.height = Math.round(H * d); CV.style.width = W + 'px'; CV.style.height = H + 'px';
    }
    var x = CV.getContext('2d'), carta = MU.fundoActual === 'carta';
    var SUAVE = '#4B6270', GRADE = 'rgba(16,33,44,.10)', FORA = '#F3F4F0', HALO = carta ? '#E6EDEB' : '#FFFFFF';
    x.setTransform(d, 0, 0, d, 0, 0); x.clearRect(0, 0, W, H);
    var a0 = map.latLngToContainerPoint([B.N, B.W]), a1 = map.latLngToContainerPoint([B.S, B.E]);
    /* esquadria da área de estudo */
    x.strokeStyle = TINTA; x.lineWidth = 1;
    x.strokeRect(Math.round(a0.x) + .5, Math.round(a0.y) + .5, Math.round(a1.x - a0.x), Math.round(a1.y - a0.y));
    /* quadrícula de coordenadas (só dentro da placa) e graduação na esquadria */
    var st = passo((a1.x - a0.x) / (B.E - B.W)), dec = st < 0.01 ? 3 : 2, lon, lat, q;
    var cx0 = Math.max(a0.x, 0), cy0 = Math.max(a0.y, 0), cx1 = Math.min(a1.x, W), cy1 = Math.min(a1.y, H);
    var lons = [], lats = [];
    for (lon = Math.ceil(B.W / st - 1e-9) * st; lon <= B.E + 1e-9; lon += st) lons.push([lon, map.latLngToContainerPoint([B.N, lon]).x]);
    for (lat = Math.ceil(B.S / st - 1e-9) * st; lat <= B.N + 1e-9; lat += st) lats.push([lat, map.latLngToContainerPoint([lat, B.W]).y]);
    if (cx1 > cx0 && cy1 > cy0) {
      x.save(); x.beginPath(); x.rect(cx0, cy0, cx1 - cx0, cy1 - cy0); x.clip();
      x.strokeStyle = GRADE; x.beginPath();
      lons.forEach(function (p) { x.moveTo(Math.round(p[1]) + .5, cy0); x.lineTo(Math.round(p[1]) + .5, cy1); });
      lats.forEach(function (p) { x.moveTo(cx0, Math.round(p[1]) + .5); x.lineTo(cx1, Math.round(p[1]) + .5); });
      x.stroke(); x.restore();
    }
    x.font = '400 10.5px "IBM Plex Mono", monospace'; x.fillStyle = SUAVE; x.strokeStyle = TINTA;
    var topo = Math.max(a0.y, 0), esq = Math.max(a0.x, 0);
    x.textAlign = 'center';
    lons.forEach(function (p) {
      if (p[1] < esq + 30 || p[1] > W - 120) return;
      x.beginPath(); x.moveTo(p[1], topo); x.lineTo(p[1], topo + 6); x.stroke();
      x.textBaseline = topo > 18 ? 'bottom' : 'top';
      x.fillText(MU.n(Math.abs(p[0]), dec) + '° O', p[1], topo > 18 ? topo - 3 : topo + 8);
    });
    lats.forEach(function (p) {
      if (p[1] < topo + 40 || p[1] > H - 70) return;
      x.beginPath(); x.moveTo(esq, p[1]); x.lineTo(esq + 6, p[1]); x.stroke();
      x.save(); x.translate(esq > 18 ? esq - 4 : esq + 9, p[1]); x.rotate(-Math.PI / 2);
      x.textBaseline = esq > 18 ? 'bottom' : 'top'; x.fillText(MU.n(p[0], dec) + '° N', 0, 0); x.restore();
    });
    /* rótulo da área fora do estudo (só no fundo «Carta», onde ela fica tracejada), na maior faixa visível */
    if (carta) {
      var faixas = [[a1.x, 0, W - a1.x, H], [0, 0, a0.x, H], [0, a1.y, W, H - a1.y], [0, 0, W, a0.y]]
        .filter(function (f) { return f[2] > 150 && f[3] > 40; })
        .sort(function (u, v) { return (v[1] === 0 && v[2] === W) - (u[1] === 0 && u[2] === W) || v[2] * v[3] - u[2] * u[3]; });   // faixa de cima primeiro, como na V2b (em baixo ficam os controlos)
      if (faixas.length) {
        var f = faixas[0], fx = f[0] + f[2] / 2, fy = f[1] + f[3] / 2;
        if (f[1] === 0 && f[3] < H) fy = Math.max(14, Math.min(fy, f[3] - 40));
        if (f[1] > 0) fy = Math.max(fy, f[1] + 40);
        if (f[3] === H) fy = H / 2;
        x.font = '400 11px "IBM Plex Mono", monospace'; x.textAlign = 'center'; x.textBaseline = 'middle';
        var tw = x.measureText('Fora da área de estudo').width + 16;
        x.fillStyle = FORA; x.fillRect(fx - tw / 2, fy - 10, tw, 20);
        x.strokeStyle = GRADE; x.strokeRect(fx - tw / 2 + .5, fy - 9.5, tw - 1, 19);
        x.fillStyle = SUAVE; x.fillText('Fora da área de estudo', fx, fy);
      }
    }
    /* rótulos: parques primeiro (prioridade), depois lugares e água, sem sobreposição */
    var caixas = [], livre = function (b) { return !caixas.some(function (c) { return b[0] < c[2] && b[2] > c[0] && b[1] < c[3] && b[3] > c[1]; }); };
    var halo = function (t, X, Y) { x.lineWidth = 3.5; x.lineJoin = 'round'; x.strokeStyle = HALO; x.strokeText(t, X, Y); x.fillText(t, X, Y); };
    if (MU.PARQUES && MU.parquesVisiveis()) {
      x.font = '600 11.5px "IBM Plex Sans", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
      MU.PARQUES.forEach(function (p) {
        var nw = map.latLngToContainerPoint(p.b.getNorthWest()), se = map.latLngToContainerPoint(p.b.getSouthEast());
        if (se.x - nw.x < 70 || se.x < 0 || nw.x > W || se.y < 0 || nw.y > H) return;
        var c = map.latLngToContainerPoint(p.centro), nome = p.f.properties.nome, tw = x.measureText(nome).width;
        var b = [c.x - tw / 2 - 3, c.y - 9, c.x + tw / 2 + 3, c.y + 9];
        if (!livre(b)) return; caixas.push(b);
        x.fillStyle = '#0B3A24'; x.lineWidth = 3.5; x.lineJoin = 'round'; x.strokeStyle = '#FFFFFF';
        x.strokeText(nome, c.x, c.y); x.fillText(nome, c.x, c.y);
      });
    }
    LUGARES.forEach(function (Lg) {
      var q = map.latLngToContainerPoint([Lg.lat, Lg.lon]);
      if (q.x < -100 || q.x > W + 100 || q.y < -30 || q.y > H + 30) return;
      x.font = Lg.k === 'a' ? 'italic 400 13px "IBM Plex Serif", serif' : '600 12px "IBM Plex Sans", sans-serif';
      var tw = x.measureText(Lg.n).width * 1.12;
      var b = Lg.rot && Math.abs(Lg.rot) > 1 ? [q.x - 9, q.y - tw / 2, q.x + 9, q.y + tw / 2] : [q.x - tw / 2, q.y - 9, q.x + tw / 2, q.y + 9];
      if (!livre(b)) return; caixas.push(b);
      x.save(); x.translate(q.x, q.y); if (Lg.rot) x.rotate(Lg.rot);
      x.textAlign = 'center'; x.textBaseline = 'middle';
      if (Lg.k === 'a') {
        x.font = 'italic 400 ' + (Lg.rot ? 13 : 12.5) + 'px "IBM Plex Serif", serif'; x.fillStyle = '#2F5A70'; x.letterSpacing = '0.12em';
        x.lineWidth = 3; x.lineJoin = 'round'; x.strokeStyle = '#A9CADB'; x.strokeText(Lg.n, 0, 0); x.fillText(Lg.n, 0, 0);
      } else if (Lg.k === 'm') {
        x.font = '500 12px "IBM Plex Sans", sans-serif'; x.fillStyle = SUAVE; x.letterSpacing = '0.06em'; halo(Lg.n, 0, 0);
      } else {
        x.font = '600 11.5px "IBM Plex Sans", sans-serif'; x.fillStyle = TINTA; x.letterSpacing = '0.04em'; x.globalAlpha = 0.82; halo(Lg.n, 0, 0);
      }
      x.restore();
    });
    x.letterSpacing = '0px';
  }

  /* ---------- pé do mapa: escala, coordenadas; zoom ---------- */
  function escala() {
    var map = MU.map, y = map.getSize().y / 2;
    var mpp = map.distance(map.containerPointToLatLng([0, y]), map.containerPointToLatLng([100, y])) / 100;
    var op = [50, 100, 200, 250, 500, 1000, 2000, 5000];
    var m = op.filter(function (v) { return v <= mpp * 100; }).pop() || 50;
    document.querySelector('#pe .bar').style.width = (m / mpp).toFixed(1) + 'px';
    document.querySelector('#pe .esc-t').textContent = m >= 1000 ? MU.n(m / 1000) + ' km' : m + ' m';
  }
  MU.verConcelho = function () {
    var map = MU.map;
    map.fitBounds([[41.138, -8.692], [41.186, -8.552]], { paddingTopLeft: [24, 56], paddingBottomRight: [24, 56], animate: false });
    // ecrã estreito: o concelho inteiro ficaria minúsculo; aproxima ~2x sobre o centro (como a maquete)
    if (map.getSize().x < 640) map.setView([41.158, -8.618], map.getZoom() + 1, { animate: false });
  };

  /* ---------- temas ---------- */
  var ICON = {
    acessibilidade: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="12" cy="12" r="9.5" stroke-dasharray="2.5 2"/><circle cx="12" cy="12" r="3.5" fill="currentColor"/></svg>',
    regra: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 21V9l5-3 5 3v12M13 21V4l8 4v13M3 21h18"/><circle cx="17" cy="14" r="1.6" fill="currentColor" stroke="none"/></svg>',
    hoje: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 7h11l-3-3M20 17H9l3 3"/></svg>',
    historico: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M3 20h18M5 20v-4h4v4M10 20v-8h4v8M15 20V6h4v14"/></svg>',
    privado: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="3" width="18" height="18"/><rect x="8" y="8" width="8" height="8" fill="currentColor" stroke="none"/></svg>'
  };
  MU.registarTema = function (t) { MU.TEMAS[t.id] = t; MU.ORDEM.push(t.id); };

  MU.abrirTema = async function (id) {
    var t = MU.TEMAS[id];
    if (!t || MU.tema === id) return;
    if (MU.tema) {
      var ant = MU.TEMAS[MU.tema];
      guardarCtx(ant.id);
      ant.desactivar();
    }
    MU.ficha(null);
    MU.tema = id;
    var painel = document.getElementById('tema-' + id);
    document.querySelectorAll('.tema').forEach(function (d) { d.classList.toggle('on', d.dataset.t === id); });
    document.querySelectorAll('.tab').forEach(function (b) {
      var on = b.dataset.t === id;
      b.classList.toggle('on', on); b.setAttribute('aria-selected', on); b.tabIndex = on ? 0 : -1;
    });
    document.getElementById('temas').scrollTop = 0;
    if (!t._montado) {
      t._montado = true;
      painel.innerHTML = '<span class="tema-sub carregando">A carregar…</span>';
      try {
        if (t.dados) await MU.carregarDados(t.dados);
        painel.innerHTML = '';
        await t.montar(painel);
        MU.moverNums(id, painel);
      } catch (e) {
        painel.innerHTML = '<span class="tema-sub">Erro: ' + e.message + '</span>';
        t._montado = false;
        throw e;
      }
    }
    if (MU.tema !== id) return;   // o utilizador mudou de tema entretanto
    painel.appendChild(document.getElementById('ctx-bloco'));   // contexto e fonte vão com o tema aberto
    // cada tema abre com o seu fundo; depois de o utilizador escolher um, essa escolha persiste
    // fundos exclusivos de um tema (p.ex. Ortofoto 1947) só aparecem nesse tema e saem dele ao mudar de tema
    var fSel = document.getElementById('fundo-select');
    MU.FUNDOS.forEach(function (f) {
      if (f.so) [].forEach.call(fSel.options, function (o) { if (o.value === f.id) o.hidden = (f.so !== id); });
    });
    var fAct = MU.FUNDOS.filter(function (f) { return f.id === MU.fundoActual; })[0];
    if (!MU.fundoManual || (fAct && fAct.so && fAct.so !== id)) MU.setFundo(t.fundo || 'carta');
    document.getElementById('fonte').innerHTML = t.fonte ? 'Fonte: ' + t.fonte : '';
    aplicarCtx(t);
    t.activar();
    MU.mostrarNums();
    MU.desenharCarta();
  };

  /* Números-chave: saem do painel (que fica para a legenda) para um cartão sobre o mapa, com X para fechar.
     Cada tema tem o seu bloco `.nums` (movido, não copiado: os temas continuam a actualizá-lo pelo id).
     Fechado = botão «Números» no mesmo sítio; a escolha lembra-se no browser; em ecrã pequeno abre fechado. */
  MU.moverNums = function (id, painel) {
    var w = document.createElement('div'); w.className = 'nums-tema'; w.dataset.t = id;
    [].slice.call(painel.querySelectorAll('.nums')).forEach(function (n) { w.appendChild(n); });
    if (w.children.length) document.getElementById('nums-corpo').appendChild(w);
  };
  MU.numsFechado = (function () {
    try { var v = localStorage.getItem('pv-nums-fechado'); if (v !== null) return v === '1'; } catch (e) { /* sem armazenamento */ }
    return window.matchMedia('(max-width:760px)').matches;
  })();
  MU.mostrarNums = function () {
    var tem = false;
    document.querySelectorAll('#nums-corpo .nums-tema').forEach(function (w) {
      var on = w.dataset.t === MU.tema; w.classList.toggle('on', on); if (on) tem = true;
    });
    document.getElementById('nums-card').classList.toggle('on', tem && !MU.numsFechado);
    document.getElementById('nums-chip').classList.toggle('on', tem && MU.numsFechado);
  };
  MU.fecharNums = function (fechar) {
    MU.numsFechado = fechar;
    try { localStorage.setItem('pv-nums-fechado', fechar ? '1' : '0'); } catch (e) { /* sem armazenamento */ }
    MU.mostrarNums();
  };
  document.getElementById('nums-x').addEventListener('click', function () { MU.fecharNums(true); });
  document.getElementById('nums-chip').addEventListener('click', function () { MU.fecharNums(false); });

  /* parâmetro do hash (#tema=acessibilidade&vista=propostas) */
  MU.param = function (nome) {
    var m = new RegExp('[#&]' + nome + '=([a-z0-9_]+)').exec(location.hash);
    return m ? m[1] : null;
  };
  /* actualiza o hash sem disparar hashchange (estado partilhável) */
  MU.setHash = function (params) {
    var s = Object.keys(params).map(function (k) { return k + '=' + params[k]; }).join('&');
    history.replaceState(null, '', '#' + s);
  };

  function temaDoHash() {
    var t = MU.param('tema');
    return (t && MU.TEMAS[t]) ? t : MU.ORDEM[0];
  }

  MU.iniciar = async function () {
    var map = MU.map = L.map('map', { zoomControl: false, zoomSnap: 0.25, zoomDelta: 0.5, wheelPxPerZoomLevel: 120 });
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
    [['placaPane', 205], ['cartaPane', 210], ['bgPane', 250], ['parquesPane', 540], ['veuPane', 560], ['limitesPane', 565], ['rotPane', 640]]
      .forEach(function (p) { map.createPane(p[0]); map.getPane(p[0]).style.zIndex = p[1]; });
    ['veuPane', 'limitesPane', 'rotPane'].forEach(function (p) { map.getPane(p).style.pointerEvents = 'none'; });
    MU.verConcelho();
    var temas = document.getElementById('temas'), tabs = document.getElementById('tabs');
    var CURTO = { acessibilidade: 'Acesso', regra: '3-30-300', hoje: 'Mudanças', historico: 'Histórico', privado: 'Privado' };
    MU.ORDEM.forEach(function (id) {
      var t = MU.TEMAS[id];
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'tab'; b.id = 'tab-' + id; b.dataset.t = id; b.tabIndex = -1;
      b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', 'false'); b.setAttribute('aria-controls', 'tema-' + id);
      b.innerHTML = (ICON[id] || '') + '<span>' + (CURTO[id] || t.rotulo) + '</span>';
      b.addEventListener('click', function () { location.hash = 'tema=' + id; });
      b.addEventListener('keydown', function (e) {
        var i = MU.ORDEM.indexOf(id), j = e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? MU.ORDEM.length - 1 : -1;
        if (j < 0) return;
        e.preventDefault(); var n = document.getElementById('tab-' + MU.ORDEM[(j + MU.ORDEM.length) % MU.ORDEM.length]); n.focus(); n.click();
      });
      tabs.appendChild(b);
      var d = document.createElement('div');
      d.className = 'tema'; d.dataset.t = id; d.setAttribute('role', 'tabpanel'); d.setAttribute('aria-labelledby', 'tab-' + id);
      d.innerHTML = '<h2 class="tema-tit">' + t.rotulo + '</h2><div class="corpo" id="tema-' + id + '"></div>';
      temas.appendChild(d);
    });
    var sel = document.getElementById('fundo-select');
    MU.FUNDOS.forEach(function (f) {
      var o = document.createElement('option'); o.value = f.id; o.textContent = f.nome; sel.appendChild(o);
    });
    sel.addEventListener('change', function () { MU.fundoManual = true; MU.setFundo(this.value); });
    window.addEventListener('hashchange', function () {
      var id = temaDoHash();
      if (id === MU.tema) { var t = MU.TEMAS[id]; if (t.aoHash) t.aoHash(); }  // só mudou um parâmetro
      else MU.abrirTema(id);
    });
    /* controlos do mapa (fora do arrasto do Leaflet) */
    ['ficha', 'topo-ctl', 'zoom', 'pe'].forEach(function (k) {
      var e = document.getElementById(k); L.DomEvent.disableClickPropagation(e); L.DomEvent.disableScrollPropagation(e);
    });
    document.querySelectorAll('#zoom button').forEach(function (b) {
      b.onclick = function () { var z = +b.dataset.z; if (z > 0) map.zoomIn(); else if (z < 0) map.zoomOut(); else MU.verConcelho(); };
    });
    map.on('mousemove', function (e) { document.querySelector('#pe .xy').textContent = MU.n(e.latlng.lat, 4) + '° N  ' + MU.n(Math.abs(e.latlng.lng), 4) + '° O'; });
    map.on('mouseout', function () { document.querySelector('#pe .xy').textContent = '—'; });
    map.on('click', function () { MU.ficha(null); });
    map.on('zoomend moveend resize', escala);
    map.on('move zoomend resize', MU.desenharCarta);
    CV = L.DomUtil.create('canvas', 'mu-carta-canvas', map.getPane('rotPane'));
    if (window.ResizeObserver) new ResizeObserver(function () { map.invalidateSize(); MU.desenharCarta(); }).observe(map.getContainer());
    /* painel em folha deslizante no telemóvel */
    var pn = document.getElementById('panel'), alca = document.getElementById('alca');
    alca.addEventListener('click', function () {
      var on = !pn.classList.contains('aberto'); pn.classList.toggle('aberto', on);
      alca.setAttribute('aria-expanded', on); alca.textContent = on ? 'Esconder o painel' : 'Mostrar camadas e números';
    });
    var rodape = function () {
      var r = document.querySelector('.pv-rodape');
      if (r && window.ResizeObserver) new ResizeObserver(function () { document.documentElement.style.setProperty('--rodh', r.offsetHeight + 'px'); }).observe(r);
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', rodape); else rodape();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(MU.desenharCarta);
    await montarContexto();
    escala();
    MU.abrirTema(temaDoHash());
  };
})();
