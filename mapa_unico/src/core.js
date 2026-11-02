/* Núcleo do mapa único do Porto Verde. Tudo vive em window.MU (sem globais soltas):
   cada tema regista-se com MU.registarTema() e só é montado quando é aberto. */
(function () {
  var BOUNDS = [[41.13, -8.7], [41.19, -8.54]];
  var MU = window.MU = { TEMAS: {}, ORDEM: [], DADOS: {}, BOUNDS: BOUNDS, tema: null };

  /* ---------- utilitários partilhados (antes duplicados em cada página) ---------- */
  MU.hexToRgb = function (h) {
    h = h.replace('#', '');
    return [parseInt(h.substr(0, 2), 16), parseInt(h.substr(2, 2), 16), parseInt(h.substr(4, 2), 16)];
  };

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
    cam.overlay = L.imageOverlay(MU.renderColored(m, o.color), o.bounds || BOUNDS, o.pane ? { pane: o.pane } : {});
    cam.setColor = function (hex) { cam.cor = hex; cam.overlay.setUrl(MU.renderColored(m, hex)); };
    return cam;
  };

  /* Linha do painel: checkbox + (cor editável | amostra) + etiqueta. */
  MU.linha = function (container, o) {
    var row = document.createElement('div');
    row.className = 'row';
    var cb = document.createElement('input');
    cb.type = 'checkbox'; cb.checked = !!o.checked;
    cb.addEventListener('change', function () { o.onToggle(this.checked); });
    row.appendChild(cb);
    var cor = null;
    if (o.color) {
      if (o.editavel) {
        cor = document.createElement('input');
        cor.type = 'color'; cor.value = o.color;
        cor.addEventListener('input', function () { o.onColor(this.value); });
      } else {
        cor = document.createElement('span');
        cor.className = 'swatch'; cor.style.backgroundColor = o.color;
      }
      row.appendChild(cor);
    }
    var lb = document.createElement('label');
    lb.textContent = o.label;
    lb.addEventListener('click', function () { cb.click(); });
    row.appendChild(lb);
    container.appendChild(row);
    return { row: row, cb: cb, cor: cor };
  };

  /* Cria camadas de máscara + linhas do painel para defs [{id,label,color,show}] (dados em
     MU.DADOS[tema.dados][id]) e guarda-as em tema._camadas, para activar/desactivar em bloco. */
  MU.addCamadas = async function (tema, box, defs, editavel) {
    tema._camadas = tema._camadas || [];
    for (var i = 0; i < defs.length; i++) {
      var c = defs[i];
      var cam = await MU.camadaMascara({ src: MU.DADOS[tema.dados][c.id], color: c.color });
      var l = { cam: cam, linha: null };
      l.linha = MU.linha(box, {
        label: c.label, checked: c.show !== false, color: c.color, editavel: editavel,
        onToggle: (function (l) {
          return function (on) {
            if (MU.tema !== tema.id) return;
            on ? l.cam.overlay.addTo(MU.map) : MU.map.removeLayer(l.cam.overlay);
          };
        })(l),
        onColor: (function (l) { return function (hex) { l.cam.setColor(hex); }; })(l)
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

  /* ---------- fundos de mapa (lista única; temas podem acrescentar o seu) ---------- */
  var ATTR = '&copy; OpenStreetMap';
  MU.FUNDOS = [
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
    MU.baseTile.bringToBack();
    MU.fundoActual = id;
    document.getElementById('fundo-select').value = id;
  };

  /* ---------- Contexto comum (limites, densidade) ---------- */
  MU.ctx = { itens: {}, estado: {} };   // estado[temaId] = {limites:{on,cor}, densidade:{on}}
  var CTX_DEF = { limites: { on: true, cor: '#444444' }, densidade: { on: false } };

  async function montarContexto() {
    var d = await MU.carregarDados('contexto');
    var map = MU.map;
    map.createPane('bgPane'); map.getPane('bgPane').style.zIndex = 250;
    map.createPane('limitesPane'); map.getPane('limitesPane').style.zIndex = 440;
    var lim = await MU.camadaMascara({ src: d.municipios, color: '#444444', pane: 'limitesPane' });
    var dens = L.imageOverlay(d.ghspop, BOUNDS, { opacity: 0.7, pane: 'bgPane' });
    MU.ctx.itens = { limites: lim, densidade: dens };
    var box = document.getElementById('ctx-rows');
    MU.ctx.rowLim = MU.linha(box, {
      label: 'Limites municipais', checked: true, color: '#444444', editavel: true,
      onToggle: function (on) { on ? lim.overlay.addTo(map) : map.removeLayer(lim.overlay); },
      onColor: function (hex) { lim.setColor(hex); }
    });
    MU.ctx.rowDens = MU.linha(box, {
      label: 'Densidade populacional', checked: false,
      onToggle: function (on) {
        on ? dens.addTo(map) : map.removeLayer(dens);
        document.getElementById('pop-legend').style.display = on ? 'block' : 'none';
      }
    });
  }

  function guardarCtx(id) {
    if (!MU.ctx.rowLim) return;
    MU.ctx.estado[id] = {
      limites: { on: MU.ctx.rowLim.cb.checked, cor: MU.ctx.itens.limites.cor },
      densidade: { on: MU.ctx.rowDens.cb.checked }
    };
  }
  function aplicarCtx(t) {
    if (!MU.ctx.rowLim) return;
    var e = MU.ctx.estado[t.id] || {
      limites: Object.assign({}, CTX_DEF.limites, (t.ctx || {}).limites),
      densidade: Object.assign({}, CTX_DEF.densidade, (t.ctx || {}).densidade)
    };
    var lim = MU.ctx.itens.limites;
    lim.setColor(e.limites.cor);
    MU.ctx.rowLim.cor.value = e.limites.cor;
    MU.ctx.rowLim.cb.checked = e.limites.on;
    MU.ctx.rowLim.cb.dispatchEvent(new Event('change'));
    MU.ctx.rowDens.cb.checked = e.densidade.on;
    MU.ctx.rowDens.cb.dispatchEvent(new Event('change'));
  }

  /* ---------- temas ---------- */
  MU.registarTema = function (t) { MU.TEMAS[t.id] = t; MU.ORDEM.push(t.id); };

  MU.abrirTema = async function (id) {
    var t = MU.TEMAS[id];
    if (!t || MU.tema === id) return;
    if (MU.tema) {
      var ant = MU.TEMAS[MU.tema];
      guardarCtx(ant.id);
      ant.desactivar();
      document.getElementById('tema-' + ant.id).style.display = 'none';
    }
    MU.tema = id;
    var painel = document.getElementById('tema-' + id);
    painel.style.display = 'block';
    document.querySelectorAll('.tabs button').forEach(function (b) {
      b.classList.toggle('active', b.dataset.tema === id);
    });
    if (!t._montado) {
      t._montado = true;
      painel.innerHTML = '<span class="tema-sub carregando">A carregar…</span>';
      try {
        if (t.dados) await MU.carregarDados(t.dados);
        painel.innerHTML = '';
        await t.montar(painel);
      } catch (e) {
        painel.innerHTML = '<span class="tema-sub">Erro: ' + e.message + '</span>';
        t._montado = false;
        throw e;
      }
    }
    if (MU.tema !== id) return;   // o utilizador mudou de separador entretanto
    // cada tema abre com o fundo da página original; depois de o utilizador escolher um, essa escolha persiste
    // fundos exclusivos de um tema (p.ex. Ortofoto 1947) só aparecem nesse tema e saem dele ao mudar de separador
    var fSel = document.getElementById('fundo-select');
    MU.FUNDOS.forEach(function (f) {
      if (f.so) [].forEach.call(fSel.options, function (o) { if (o.value === f.id) o.hidden = (f.so !== id); });
    });
    var fAct = MU.FUNDOS.filter(function (f) { return f.id === MU.fundoActual; })[0];
    if (!MU.fundoManual || (fAct && fAct.so && fAct.so !== id)) MU.setFundo(t.fundo || 'positron');
    document.getElementById('fonte').innerHTML = t.fonte || '';
    aplicarCtx(t);
    t.activar();
  };

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
    var map = MU.map = L.map('map').setView([41.155, -8.63], 13);
    var tabs = document.getElementById('tabs');
    MU.ORDEM.forEach(function (id) {
      var t = MU.TEMAS[id];
      var b = document.createElement('button');
      b.dataset.tema = id; b.textContent = t.rotulo;
      b.addEventListener('click', function () { location.hash = 'tema=' + id; });
      tabs.appendChild(b);
      var d = document.createElement('div');
      d.id = 'tema-' + id; d.style.display = 'none';
      document.getElementById('temas').appendChild(d);
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
    await montarContexto();
    MU.abrirTema(temaDoHash());
  };
})();
